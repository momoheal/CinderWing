"""M2 任务事件源：轮询豆包工作客户端的 IndexedDB，把真实 Agent 任务的
生命周期（开始 / 进度 / 需要决策 / 完成 / 失败）翻译成 Bubble 事件。

数据位置：
  IndexedDB 库 samantha-web（db id=1）→ 对象存储 store
  → 键 default-chat-im-protocol-store
  → 值路径 state.mainTaskDataMap（按任务 UUID 索引）

实测字段口径（2026-10，tools/_m2_watch.py 抓包）：
  * 真正的 Agent 任务标记在
        requestQuery.syncTask.option.general_task_param
    （兜底 syncTask.ext.is_general_task == "1"）；普通聊天回合无此字段。
  * 顶层 stage 恒为 "sync"，不能用来判断生命周期。
  * 任务文本：syncTask.messages[0].content_block[].content.text_block.text。
  * receivedMessages[*].extra 里才有真实状态：
        status 4=已接收/流式, stage 1, contentStatus 2
        ext.is_finish == "1" 表示本轮结束
        ext.mode_downgrade_reason == "success" 表示成功
        final_status.message（sentMessages 侧）== "Success"
    内容块 block_type：10000 文本 / 10040 思考 / 10091 计时 /
        10019 shell 文件操作 / 10024 通用工具 / 10083 电脑操作 /
        10025 搜索 / 10006 网页阅读。
  * 没有原生进度百分比，按阶段合成单调递增的伪进度。
半写快照会出现 agent 标记短暂丢失 / 消息为空，需做防抖。
"""
import contextlib
import io
import json
import pathlib
import shutil
import tempfile
import time

from PySide6.QtCore import QObject, QTimer

from app import paths

SRC = pathlib.Path.home() / (
    r"AppData\Local\DoubaoWork\User Data\Default\IndexedDB")
LEVELDB_NAME = "chrome_doubaowork-chat_0.indexeddb.leveldb"
BLOB_NAME = "chrome_doubaowork-chat_0.indexeddb.blob"

LOG_PATH = paths.log_path()

# 内容块类型（实测）
B_TEXT = 10000
B_THINK = 10040
B_ELAPSED = 10091
B_SHELL = 10019
B_TOOL = 10024
B_CUA = 10083
B_SEARCH = 10025
B_LINK = 10006
B_GENIMG = 10010        # AI 生图工具结果 gen_image_block
B_GUI = 10068           # GUI 自动化工具 gui_tool_block（Wait/点击等）
B_ASK = 10082           # 交互提问 interaction_ask_block（需要用户回答=决策点）
B_RICHMEDIA = 10084     # 富媒体排版容器 rich_media_layout_block（展示用，不计工具）
B_LOCALFILE = 10063     # 本地文件引用 local_file_block（展示用，不计工具）
TOOL_BLOCKS = {B_SHELL, B_TOOL, B_CUA, B_SEARCH, B_LINK, B_GENIMG, B_GUI}
KNOWN_BLOCKS = TOOL_BLOCKS | {
    B_TEXT, B_THINK, B_ELAPSED, B_ASK, B_RICHMEDIA, B_LOCALFILE}


def _log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} [task_source] {msg}\n")
    except OSError:
        pass


class _TaskState:
    __slots__ = ("kind", "pct", "name", "conversation_id", "section_id",
                 "reported_terminal", "missing_rounds")

    def __init__(self, kind, pct, name, conversation_id, section_id):
        self.kind = kind
        self.pct = pct
        self.name = name
        self.conversation_id = conversation_id
        self.section_id = section_id
        self.reported_terminal = kind in ("DONE", "FAIL")
        self.missing_rounds = 0


class DoubaoTaskSource(QObject):
    """定时把豆包工作任务表同步给 Bubble。

    on_event(kind, body, key, name, progress, conv_id, section_id)
        一般直接接 bubble.notify；
    on_progress(key, percent, body, conv_id, section_id)
        接 bubble.update_progress。
    """

    def __init__(self, bubble, on_event, on_progress,
                 interval_ms=3000, parent=None):
        super().__init__(parent)
        self.bubble = bubble
        self.on_event = on_event
        self.on_progress = on_progress
        self._work_root = pathlib.Path(tempfile.gettempdir()) / \
            "cinderwing_idb"
        # 清掉旧版本（每轮固定目录时代）可能残留的 leveldb/blob
        for legacy in ("leveldb", "blob"):
            shutil.rmtree(self._work_root / legacy, ignore_errors=True)
        self._work = self._work_root / "run"
        self._known: dict[str, _TaskState] = {}
        self._primed = False           # 首轮只登记不播报（不回播历史）
        self._unknown_blocks: set[int] = set()
        self._ask_status_seen: set[int] = set()  # interaction_ask_block 状态采样
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(interval_ms)
        QTimer.singleShot(1200, self.poll)

    # ---- 数据读取 -------------------------------------------------------
    def _snapshot(self):
        # 每轮用全新目录：上一轮的 leveldb/blob 句柄可能还没释放，
        # Windows 上删不掉，复用目录会让 copytree 持续 FileExistsError。
        try:
            work = pathlib.Path(tempfile.mkdtemp(
                prefix="run_", dir=str(self._work_root)))
        except FileNotFoundError:
            self._work_root.mkdir(parents=True, exist_ok=True)
            work = pathlib.Path(tempfile.mkdtemp(
                prefix="run_", dir=str(self._work_root)))
        # 顺手清理旧轮次目录（删不掉就算了，下轮再试）
        for old in self._work_root.glob("run_*"):
            if old != work:
                shutil.rmtree(old, ignore_errors=True)
        self._work = work
        ld, bl = work / "leveldb", work / "blob"
        src_ld = SRC / LEVELDB_NAME
        if not src_ld.exists():
            return False
        # 先拷 blob（不可变大文件），再拷 leveldb，缩小与运行中客户端的竞态
        src_bl = SRC / BLOB_NAME
        if src_bl.exists():
            shutil.copytree(src_bl, bl)
        shutil.copytree(src_ld, ld)
        return True

    def _find_blob_by_size(self, size: int) -> bytes | None:
        """blob 编号表对不上时的兜底：按 envelope 声明的精确大小找文件。

        Chromium 的大值记录存在 .blob 目录，leveldb 里只留编号索引；
        运行中拷贝时新旧索引可能混排，导致编号指向已轮换的旧文件，
        而 envelope 里声明的字节大小是和数据记录一起原子写入的，最可靠。
        """
        bl = self._work / "blob"
        if not bl.exists():
            return None
        candidates = []
        for p in bl.rglob("*"):
            if p.is_file():
                try:
                    if p.stat().st_size == size:
                        candidates.append(p)
                except OSError:
                    continue
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for p in candidates:
            try:
                return p.read_bytes()
            except OSError:
                continue
        return None

    def _read_default_store_state(self, w):
        """专门解析 default-chat-im-protocol-store 的最新 live 值。

        返回 state dict（含 mainTaskDataMap），失败返回 None。
        """
        import io
        import ccl_simplesnappy
        from ccl_chromium_reader.ccl_chromium_indexeddb import (
            BlinkTrailer, IndexedDb, _le_varint_from_bytes)
        from ccl_chromium_reader.serialization_formats import (
            ccl_blink_value_deserializer as bvd,
            ccl_v8_value_deserializer as v8d)

        DB_ID = STORE_ID = 1
        raw = w._raw_db
        needle = "default-chat-im-protocol-store".encode("utf-16-be")
        prefix = IndexedDb.make_prefix(DB_ID, STORE_ID, 1)
        best = None
        for rec in raw._fetched_records:
            if (rec.key.startswith(prefix) and needle in rec.key
                    and str(rec.state) == "KeyState.Live"):
                if best is None or rec.seq > best.seq:
                    best = rec
        if best is None:
            return None
        raw_key = best.key[len(prefix):]
        _, lead = _le_varint_from_bytes(best.value)
        first_buf = best.value[len(lead):]

        def parse(buf: bytes):
            if not buf or buf[0] != 0xFF:
                return None
            ver, vr = _le_varint_from_bytes(buf[1:])
            i = 1 + len(vr)
            if ver == 0x11:
                flag = buf[i]
                if flag == 0x01:  # kReplaceWithBlob
                    i += 1
                    size, v1 = _le_varint_from_bytes(buf[i:])
                    i += len(v1)
                    blob_index, v2 = _le_varint_from_bytes(buf[i:])
                    i += len(v2)
                    data = None
                    try:
                        fh = raw.get_blob(DB_ID, STORE_ID, raw_key, blob_index)
                        try:
                            data = fh.read()
                        finally:
                            fh.close()
                    except (FileNotFoundError, KeyError, ValueError):
                        data = self._find_blob_by_size(size)
                    if data is None:
                        _log(f"blob 缺失：size={size} index={blob_index}，"
                             f"本轮快照可能不完整，下轮重试")
                        return None
                    return parse(data)
                if flag == 0x02:  # kCompressedWithSnappy
                    i += 1
                    return parse(ccl_simplesnappy.decompress(
                        io.BytesIO(buf[i:])))
                raise ValueError(f"unexpected SSV flag {flag}")
            if ver >= BlinkTrailer.MIN_WIRE_FORMAT_VERSION_FOR_TRAILER:
                i += BlinkTrailer.TRAILER_SIZE
            d = v8d.Deserializer(
                io.BytesIO(buf[i:]),
                host_object_delegate=bvd.BlinkV8Deserializer().read)
            return d.read()

        try:
            value = parse(first_buf)
        except Exception as e:
            _log(f"default store 解析失败：{type(e).__name__}: {e}")
            return None
        if isinstance(value, dict):
            return value.get("state")
        return None

    def _read_tasks(self):
        from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB
        ld, bl = self._work / "leveldb", self._work / "blob"
        w = WrappedIndexDB(ld, bl if bl.exists() else None)
        try:
            # 主路径：专门解析 default-chat-im-protocol-store（带 blob 兜底）
            state = self._read_default_store_state(w)
            if isinstance(state, dict):
                tmap = state.get("mainTaskDataMap")
                if isinstance(tmap, dict) and tmap:
                    return tmap
                _log("default store 已读到，但 mainTaskDataMap 为空")

            # 兜底：旧版 reader 全量遍历（客户端未把大值外置到 blob 时有效）
            tasks = {}
            for dbid in w.database_ids:
                if dbid.name != "samantha-web":
                    continue
                db = w[dbid.dbid_no]
                with contextlib.redirect_stdout(io.StringIO()):
                    recs = list(db["store"].iterate_records(
                        errors_to_stdout=False,
                        bad_deserializer_data_handler=lambda key, rec: None))
                for rec in recs:
                    state = rec.value.get("state") if isinstance(rec.value, dict) \
                        else None
                    tmap = state.get("mainTaskDataMap") if isinstance(state, dict) \
                        else None
                    if isinstance(tmap, dict):
                        tasks.update(tmap)
            return tasks
        finally:
            # 释放 leveldb / blob 文件句柄，否则下轮快照目录删不掉
            try:
                w.close()
            except Exception:
                pass

    # ---- 字段提取 -------------------------------------------------------
    @staticmethod
    def _is_real_agent_task(t):
        q = t.get("requestQuery", {}) if isinstance(t, dict) else {}
        st = q.get("syncTask", {}) if isinstance(q, dict) else {}
        if not isinstance(st, dict):
            return False
        opt = st.get("option", {})
        if isinstance(opt, dict) and opt.get("general_task_param"):
            return True
        ext = st.get("ext", {})
        return isinstance(ext, dict) and ext.get("is_general_task") == "1"

    @staticmethod
    def _query_text(t):
        q = t.get("requestQuery", {}) or {}
        st = q.get("syncTask", {}) if isinstance(q, dict) else {}
        msgs = st.get("messages", []) if isinstance(st, dict) else []
        for m in msgs[:2]:
            for blk in (m.get("content_block") or []):
                txt = (blk.get("content", {}) or {}).get(
                    "text_block", {}).get("text")
                if txt:
                    return txt.strip()
        # 兜底：sentMessages 里的 brief / 文本块
        for v in (t.get("sentMessages", {}) or {}).values():
            ex = v.get("extra", {}) or {}
            brief = (ex.get("ext", {}) or {}).get("brief")
            if isinstance(brief, str) and brief.strip():
                return brief.strip()
        return ""

    @staticmethod
    def _conv_ids(t):
        # 实测会话 id 在 sentMessages[*].extra 内（conversation_id/section_id）
        for v in (t.get("sentMessages", {}) or {}).values():
            ex = v.get("extra", {}) or {}
            cid = (v.get("conversation_id") or v.get("conversationId")
                   or ex.get("conversation_id"))
            sid = (v.get("section_id") or v.get("last_section_id")
                   or ex.get("section_id") or ex.get("last_section_id"))
            if cid:
                return cid, sid
        return None, None

    def _extract(self, t):
        """返回 (kind, pct, detail)。detail 含块计数/状态，供正文使用。"""
        rmsgs = t.get("receivedMessages", {}) or {}
        smsg = t.get("sentMessages", {}) or {}

        n_think = n_tool = n_text = 0
        last_is_answer = False
        waiting = False
        finished = False
        reason_ok = False
        reason_bad = False
        ask_block = None

        for v in rmsgs.values():
            ex = v.get("extra", {}) or {}
            ext2 = ex.get("ext", {}) or {}
            if ext2.get("is_finish") == "1":
                finished = True
                reason = ext2.get("mode_downgrade_reason")
                if reason == "success":
                    reason_ok = True
                elif reason:
                    reason_bad = True
            blocks = ex.get("content_blocks_v2", []) or []
            if blocks:
                lb = blocks[-1]
                if (lb.get("block_type") == B_TEXT and lb.get("is_finish")
                        and not lb.get("parent_id")):
                    last_is_answer = True
            for cb in blocks:
                bt = cb.get("block_type")
                if bt not in KNOWN_BLOCKS and bt not in self._unknown_blocks:
                    self._unknown_blocks.add(bt)
                    _log(f"unknown block_type={bt} "
                         f"content_keys={list((cb.get('content') or {}).keys())}")
                if bt == B_ASK:
                    # interaction_ask_block：Agent 弹出结构化问题等用户回答。
                    # 实测样本：status=2 表示已关闭（回答/超时，文案为
                    # “未提供回答”）；status=1 判定为待回答（WAITING）。
                    # 题型 type：1 单选 / 2 多选 / 3 自由文本；
                    # 选择题选项在 questions[].options[]（option_id/label）。
                    ab = (cb.get("content", {}) or {}).get(
                        "interaction_ask_block", {}) or {}
                    st = ab.get("status")
                    if st not in self._ask_status_seen:
                        self._ask_status_seen.add(st)
                        _log(f"interaction_ask_block status={st}")
                    if st == 1:
                        waiting = True
                        ask_block = ab
                # 注意：不能用块正文里的 permission 等字样判 WAITING——
                # shell 输出/Agent 正文里会出现 local_permissions 等内容，
                # 实测造成误报。WAITING 只认结构化信号（interaction_ask_block
                # 待回答状态，以及下方 option 钩子）。
                if bt == B_THINK:
                    n_think += 1
                elif bt in TOOL_BLOCKS:
                    n_tool += 1
                elif bt == B_TEXT:
                    n_text += 1

        sent_final_ok = sent_final_bad = False
        for v in smsg.values():
            ex = v.get("extra", {}) or {}
            fs = ex.get("final_status")
            if isinstance(fs, dict) and fs.get("message"):
                if fs["message"] == "Success":
                    sent_final_ok = True
                else:
                    sent_final_bad = True

        # 选项层的交互标记（当前观测为 "<Undefined>"，留作钩子）
        opt = ((t.get("requestQuery", {}) or {}).get("syncTask", {}) or {}) \
            .get("option", {}) or {}
        pi = opt.get("permission_interact")
        if pi and pi != "<Undefined>":
            waiting = True

        # ---- 状态判定（终态只认 is_finish；reason 仅终态时用于成败）----
        if finished:
            kind = "FAIL" if (reason_bad or
                              (sent_final_bad and not sent_final_ok
                               and not reason_ok)) else "DONE"
            pct = 100.0
        elif waiting:
            kind, pct = "WAITING", None
        elif rmsgs:
            kind = "PROGRESS"
            # ---- 合成伪进度（单调，封顶 96）----
            pct = 8.0
            if n_think:
                pct = 18.0
            if n_tool:
                pct = max(pct, min(28.0 + n_tool * 7.0, 82.0))
            if last_is_answer:
                pct = max(pct, 90.0)
            pct = min(pct, 96.0)
        else:
            kind, pct = "START", 4.0

        detail = {"think": n_think, "tool": n_tool, "text": n_text}

        # 结构化决策问题（选项）：只在待回答状态下带给气泡
        ask = None
        if ask_block:
            questions = []
            for q in ask_block.get("questions", []) or []:
                if not isinstance(q, dict):
                    continue
                cap = q.get("question_capability") or {}
                opts = []
                for o in q.get("options", []) or []:
                    if isinstance(o, dict):
                        label = o.get("label") or o.get("text")
                        if label:
                            opts.append({"id": str(o.get("option_id")),
                                         "label": str(label)})
                questions.append({
                    "title": q.get("title") or "请回答以下问题",
                    "type": q.get("type"),
                    "options": opts,
                    "allow_text": bool(cap.get("allow_text")),
                })
            if questions:
                ask = {"questions": questions}
        return kind, pct, detail, ask

    # ---- 轮询主循环 -----------------------------------------------------
    def poll(self):
        try:
            if not self._snapshot():
                return
            cur = self._read_tasks()
        except Exception as e:
            _log(f"poll skip: {repr(e)[:160]}")
            return

        seen = set()
        for tid, t in cur.items():
            if not isinstance(t, dict) or not self._is_real_agent_task(t):
                continue
            seen.add(tid)
            name = (self._query_text(t) or tid[:8])
            if len(name) > 26:
                name = name[:26] + "…"
            kind, pct, detail, ask = self._extract(t)
            cid, sid = self._conv_ids(t)
            old = self._known.get(tid)

            if old is None:
                self._known[tid] = _TaskState(kind, pct, name, cid, sid)
                if self._primed and kind != "DONE":
                    self.on_event("START", f"任务开始：{name}", tid, name, 4.0,
                                  cid, sid)
                continue

            # 半写快照防抖：关键字段突然"倒退"时保留旧判定一轮
            if kind == "START" and old.kind in ("PROGRESS", "WAITING"):
                continue
            old.missing_rounds = 0
            if name:
                old.name = name
            if cid:
                old.conversation_id, old.section_id = cid, sid

            if kind == "WAITING":
                if old.kind != "WAITING":
                    if ask:
                        body = (ask["questions"][0].get("title")
                                or f"需要你决策：{name}")
                    else:
                        body = f"需要你决策：{name}"
                    self.on_event("WAITING", body, tid, name, old.pct or 0.0,
                                  old.conversation_id, old.section_id, ask)
                old.kind = "WAITING"
                continue

            if kind in ("DONE", "FAIL") and not old.reported_terminal:
                body = (f"任务完成：{name}" if kind == "DONE"
                        else f"任务失败：{name}")
                self.on_event(kind, body, tid, name, 100.0,
                              old.conversation_id, old.section_id)
                old.kind, old.pct = kind, 100.0
                old.reported_terminal = True
                continue

            if kind == "PROGRESS":
                new_pct = max(pct or 0.0, old.pct or 0.0)
                if old.kind in ("START", "WAITING"):
                    # 新任务进入运行，或决策完毕恢复运行：发状态事件换气泡标题
                    self.on_event("PROGRESS", f"任务进行中：{name}", tid,
                                  name, new_pct,
                                  old.conversation_id, old.section_id)
                elif new_pct - (old.pct or 0.0) >= 2.0:
                    self.on_progress(tid, new_pct, f"任务进行中：{name}",
                                     old.conversation_id, old.section_id)
                old.kind, old.pct = "PROGRESS", new_pct

        # 消失处理：终态任务保留登记（防止回闪重复播报）；未终态的连续 3 轮
        # 不见才按完成处理（半写快照会短暂缺任务）
        for tid, old in list(self._known.items()):
            if tid in seen:
                continue
            old.missing_rounds += 1
            if old.reported_terminal:
                if old.missing_rounds > 20:
                    self._known.pop(tid, None)
                continue
            if old.missing_rounds >= 3:
                self.on_event("DONE", f"任务完成：{old.name}", tid,
                              old.name, 100.0,
                              old.conversation_id, old.section_id)
                old.kind, old.pct = "DONE", 100.0
                old.reported_terminal = True

        self._primed = True
