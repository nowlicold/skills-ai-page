"""
通用执行规格：根据 metadata.execution 驱动 HTTP 调用，不写死具体 skill。
支持 type: http（单次请求）、ppt_task（创建任务+轮询直至终态）。
占位符：{{ENV:VAR}}、{{prompt}}、{{param.xxx}}、ppt_task 轮询 URL 支持 {{task_id}}。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# 内置参数提取器：从用户 prompt 中提取结构化参数，供 execution 中 {{param.xxx}} 使用
def _extract_youtube_video_id(prompt: str) -> str | None:
    if not (prompt or "").strip():
        return None
    m = re.search(
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        prompt,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m = re.search(r"\b([a-zA-Z0-9_-]{11})\b", prompt)
    if m:
        return m.group(1)
    return None


PARAM_EXTRACTORS: dict[str, callable] = {
    "youtube_video_id": _extract_youtube_video_id,
}

USER_AGENT = "SkillsAI-Platform/1.0 (Felo-OpenAPI-Client)"


def _substitute(value: Any, prompt: str, params: dict[str, str]) -> Any:
    """递归替换 {{ENV:VAR}}、{{prompt}}、{{param.xxx}}、{{key}}（key 为 params 中的键，便于 body 直接写 {{url}} 等）。"""
    if isinstance(value, str):
        s = value
        for key, val in os.environ.items():
            s = s.replace(f"{{{{ENV:{key}}}}}", (val or "").strip().strip("'\""))
        s = s.replace("{{prompt}}", prompt)
        for k, v in params.items():
            s = s.replace(f"{{{{param.{k}}}}}", v or "")
            s = s.replace(f"{{{{{k}}}}}", v or "")
        return s
    if isinstance(value, dict):
        return {k: _substitute(v, prompt, params) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, prompt, params) for v in value]
    return value


def _get_by_path(data: dict, path: str) -> Any:
    """取 data['a']['b']['c']，path 为 'a.b.c'。"""
    cur = data
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _substitute_context(value: Any, context: dict[str, str]) -> Any:
    """用 context 的键值替换 {{key}}、{{ENV:VAR}}（context 中 ENV:VAR 已展开）。递归处理 dict/list。"""
    if isinstance(value, str):
        s = value
        for k, v in context.items():
            s = s.replace(f"{{{{{k}}}}}", (v or "").strip().strip("'\""))
        return s
    if isinstance(value, dict):
        return {k: _substitute_context(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_context(v, context) for v in value]
    return value


def _format_response(data: dict, fmt: str, spec: dict) -> str:
    """按 execution.response.format 格式化 API 返回体。"""
    resp_cfg = spec.get("response") or {}
    if fmt == "answer_sources":
        d = _get_by_path(data, resp_cfg.get("data_path") or "data")
        if not isinstance(d, dict):
            return json.dumps(data, ensure_ascii=False, indent=2)
        parts = []
        answer = (d.get("answer") or "").strip()
        if answer:
            parts.append(f"## 回答\n\n{answer}")
        qa = d.get("query_analysis")
        if isinstance(qa, dict) and qa.get("queries"):
            parts.append("## 检索词\n\n" + "、".join(str(x) for x in qa["queries"] if x))
        elif isinstance(qa, list) and qa:
            parts.append("## 检索词\n\n" + "、".join(str(x) for x in qa if x))
        resources = d.get("resources")
        if isinstance(resources, list) and resources:
            lines = []
            for r in resources[:15]:
                if isinstance(r, dict):
                    link = r.get("link") or r.get("url")
                    title = (r.get("title") or "").strip() or link or "链接"
                    if link:
                        lines.append(f"- [{title}]({link})")
            if lines:
                parts.append("## 参考来源\n\n" + "\n".join(lines))
        return "\n\n".join(parts) if parts else json.dumps(data, ensure_ascii=False, indent=2)

    if fmt == "youtube_subtitles":
        inner = _get_by_path(data, resp_cfg.get("data_path") or "data")
        if not isinstance(inner, dict):
            return json.dumps(data, ensure_ascii=False, indent=2)
        title = (inner.get("title") or "").strip() or "（无标题）"
        contents = inner.get("contents")
        if not isinstance(contents, list):
            return f"## 视频标题\n\n{title}\n\n（该视频暂无可用字幕或返回格式异常。）"
        lines = [seg.get("text", "").strip() for seg in contents if isinstance(seg, dict) and seg.get("text")]
        if not lines:
            return f"## 视频标题\n\n{title}\n\n（该视频暂无可用字幕。）"
        return f"## 视频标题\n\n{title}\n\n## 字幕\n\n" + "\n\n".join(lines)

    if fmt == "web_page":
        inner = _get_by_path(data, resp_cfg.get("data_path") or "data")
        if isinstance(inner, dict):
            title = (inner.get("title") or "").strip() or ""
            content = (inner.get("content") or inner.get("text") or "").strip()
            if title:
                return f"## {title}\n\n{content}" if content else f"## {title}"
            if content:
                return content
        return json.dumps(data, ensure_ascii=False, indent=2)

    if fmt == "list":
        inner = _get_by_path(data, resp_cfg.get("data_path") or "data")
        items = []
        if isinstance(inner, list):
            items = inner[:30]
        elif isinstance(inner, dict) and "items" in inner:
            items = inner["items"][:30] if isinstance(inner["items"], list) else []
        lines = []
        for it in items:
            if isinstance(it, dict):
                title = (it.get("title") or it.get("name") or "").strip() or "（无标题）"
                url = it.get("url") or it.get("link")
                if url:
                    lines.append(f"- [{title}]({url})")
                else:
                    lines.append(f"- {title}")
            elif isinstance(it, str):
                lines.append(f"- {it}")
        return "\n".join(lines) if lines else json.dumps(data, ensure_ascii=False, indent=2)

    # text: 单一路径取字符串
    content_path = resp_cfg.get("content_path")
    if content_path:
        text = _get_by_path(data, content_path)
        if isinstance(text, str):
            return text.strip()
    return json.dumps(data, ensure_ascii=False, indent=2)


def _extract_result_data(data: dict, fmt: str, spec: dict) -> dict | None:
    """从 API 返回中提取结构化 result_data，供前端按 result_format 渲染。"""
    resp_cfg = spec.get("response") or {}
    data_path = resp_cfg.get("data_path") or "data"
    d = _get_by_path(data, data_path)
    if not isinstance(d, dict):
        return None
    if fmt == "youtube_subtitles":
        title = (d.get("title") or "").strip() or "（无标题）"
        contents = d.get("contents") or []
        subtitles = []
        for seg in contents:
            if isinstance(seg, dict) and seg.get("text") is not None:
                subtitles.append({
                    "start": seg.get("start"),
                    "end": seg.get("end"),
                    "text": (seg.get("text") or "").strip(),
                })
        return {"title": title, "subtitles": subtitles}
    if fmt == "answer_sources":
        answer = (d.get("answer") or "").strip()
        resources = d.get("resources") or []
        sources = []
        for r in resources[:30]:
            if isinstance(r, dict):
                link = r.get("link") or r.get("url")
                title_r = (r.get("title") or "").strip() or link or "链接"
                if link:
                    sources.append({"title": title_r, "url": link})
        return {"answer": answer, "sources": sources}
    if fmt == "web_page":
        title = (d.get("title") or "").strip() or ""
        content = (d.get("content") or d.get("text") or "").strip()
        return {"title": title, "content": content}
    if fmt == "list":
        raw = d.get("items") if isinstance(d.get("items"), list) else []
        items = []
        for it in raw[:30]:
            if isinstance(it, dict):
                items.append({
                    "title": (it.get("title") or it.get("name") or "").strip() or "（无标题）",
                    "url": it.get("url") or it.get("link"),
                    "description": (it.get("description") or "").strip() or None,
                })
            elif isinstance(it, str):
                items.append({"title": it, "url": None, "description": None})
        return {"items": items}
    return None


def run_http(
    spec: dict, prompt: str, explicit_params: dict | None = None
) -> tuple[bool, str, str | None, dict | None]:
    """
    按 metadata.execution (type=http) 执行一次 HTTP 请求，返回 (是否成功, 内容或错误信息)。
    spec 结构示例：
      type: "http"
      method: "GET" | "POST"
      url: "https://...", 可含 {{ENV:FELO_API_KEY}}、{{param.video_code}}
      headers: { "Authorization": "Bearer {{ENV:FELO_API_KEY}}" }
      body: { "query": "{{prompt}}" }   # POST 时
      query_params: { "video_code": "{{param.video_code}}" }  # GET 时
      param_extractors: { "video_code": "youtube_video_id" }   # 从 prompt 提取 param
      response:
        success_codes: [0, "ok", 200, "OK"]  # 或 success_path + success_values
        format: "answer_sources" | "youtube_subtitles" | "text"
        data_path: "data"  # 可选
        content_path: "data.answer"  # format=text 时
    """
    if (spec.get("type") or "").lower() != "http":
        return False, "execution.type 非 http，无法执行", None, None

    # 1) 解析 param_extractors：优先用 explicit_params（如表单提交），否则从 prompt 提取
    params: dict[str, str] = {}
    extractors = spec.get("param_extractors") or {}
    for param_name, extractor_name in extractors.items():
        if explicit_params and param_name in explicit_params:
            v = explicit_params.get(param_name)
            if v is not None and str(v).strip():
                params[param_name] = str(v).strip()
                continue
        fn = PARAM_EXTRACTORS.get(extractor_name)
        if fn and callable(fn):
            val = fn(prompt)
            params[param_name] = val if val is None else str(val)
    # 表单/请求中的其它参数也并入 params，供 body 中 {{url}}、{{output_format}} 等占位符替换
    if explicit_params:
        for k, v in explicit_params.items():
            if k in params:
                continue
            if v is not None and str(v).strip():
                params[k] = str(v).strip()

    # 2) 替换占位符
    url = _substitute(spec.get("url") or "", prompt, params)
    if not url.strip():
        return False, "execution.url 为空", None, None
    headers = _substitute(spec.get("headers") or {}, prompt, params)
    if not isinstance(headers, dict):
        headers = {}
    headers["User-Agent"] = USER_AGENT
    method = (spec.get("method") or "GET").upper()
    query_params = spec.get("query_params")
    if query_params:
        query_params = _substitute(query_params, prompt, params)
        if isinstance(query_params, dict):
            qs = urllib.parse.urlencode({k: v for k, v in query_params.items() if v is not None and str(v).strip()})
            url = f"{url.rstrip('?')}{'&' if '?' in url else '?'}{qs}"

    body = None
    if method == "POST":
        body_obj = _substitute(spec.get("body") or {}, prompt, params)
        if isinstance(body_obj, dict):
            body = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

    timeout = int(spec.get("timeout") or 60)
    if timeout <= 0 or timeout > 300:
        timeout = 60
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        msg = f"请求失败（HTTP {e.code}）"
        try:
            j = json.loads(err_body) if err_body.strip() else {}
            code = j.get("code") or j.get("error_code")
            detail = j.get("message") or j.get("error_message") or ""
            if code or detail:
                msg += f"：{code or ''} {detail}".strip()
            else:
                msg += f"。{(' ' + err_body[:200]) if err_body else ''}"
        except Exception:
            if err_body:
                msg += f"。响应片段：{err_body[:200]}"
        return False, msg, None, None
    except Exception as e:
        return False, f"请求异常：{e!s}", None, None

    try:
        data = json.loads(raw)
    except Exception:
        return True, raw, None, None

    resp_cfg = spec.get("response") or {}
    fmt = resp_cfg.get("format") or "text"
    success_codes = resp_cfg.get("success_codes")
    # 成功判定：先看 success_codes；若未命中则对已知 format 看是否有有效内容，避免 analyzer 只填了 [200] 而 API 返回 code:"OK" 导致误判失败
    if success_codes is not None:
        code_val = data.get("code") or data.get("status")
        ok_vals = [str(c) for c in success_codes]
        if code_val not in success_codes and str(code_val) not in ok_vals:
            # 兼容：按 format 看是否有有效结构，有则视为成功（避免 analyzer 只填 [0] 而 API 返回 code:"OK"/status:200）
            if fmt == "answer_sources" and isinstance(data.get("data"), dict) and data["data"].get("answer"):
                pass
            elif fmt == "youtube_subtitles" and isinstance(data.get("data"), dict):
                inner = data["data"]
                if isinstance(inner.get("contents"), list) or inner.get("title") is not None:
                    pass
                else:
                    return False, data.get("message") or json.dumps(data, ensure_ascii=False, indent=2), None, None
            else:
                return False, data.get("message") or json.dumps(data, ensure_ascii=False, indent=2), None, None
    try:
        content = _format_response(data, fmt, spec)
    except Exception as e:
        content = json.dumps(data, ensure_ascii=False, indent=2) + f"\n\n(格式化异常: {e})"
    result_data = _extract_result_data(data, fmt, spec)
    return True, content, fmt, result_data


def run_ppt_task(spec: dict, prompt: str) -> tuple[bool, str]:
    """
    按 metadata.execution (type=ppt_task) 执行：创建任务 → 轮询直至终态 → 返回 ppt_url / 错误信息。
    spec 示例：
      type: "ppt_task"
      create_url: "https://openapi.felo.ai/v2/ppts"
      create_body: { "query": "{{prompt}}" }
      headers: { "Authorization": "Bearer {{ENV:FELO_API_KEY}}" }
      poll_url_template: "https://openapi.felo.ai/v2/tasks/{{task_id}}/historical"
      poll_interval: 5
      max_wait: 600
      task_id_path: "data.task_id"
      status_path: "data.task_status"
      success_statuses: ["COMPLETED", "SUCCESS"]
      failure_statuses: ["FAILED", "ERROR", "EXPIRED", "CANCELED", "PENDING"]
      result:
        ppt_url: "data.ppt_url"
        live_doc_url: "data.live_doc_url"
        error_message: "data.error_message"
    """
    if (spec.get("type") or "").lower() != "ppt_task":
        return False, "execution.type 非 ppt_task，无法执行"

    params: dict[str, str] = {}
    create_url = _substitute(spec.get("create_url") or "", prompt, params)
    if not create_url.strip():
        return False, "execution.create_url 为空"
    headers = _substitute(spec.get("headers") or {}, prompt, params)
    if not isinstance(headers, dict):
        headers = {}
    headers["User-Agent"] = USER_AGENT
    body_obj = _substitute(spec.get("create_body") or {}, prompt, params)
    body = json.dumps(body_obj, ensure_ascii=False).encode("utf-8") if isinstance(body_obj, dict) else None
    if body is not None:
        headers.setdefault("Content-Type", "application/json")

    timeout = int(spec.get("timeout") or 60)
    if timeout <= 0 or timeout > 120:
        timeout = 60
    req = urllib.request.Request(create_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        msg = f"创建 PPT 任务失败（HTTP {e.code}）"
        try:
            j = json.loads(err_body) if err_body.strip() else {}
            msg += f"：{j.get('message') or j.get('error_message') or err_body[:200]}"
        except Exception:
            if err_body:
                msg += f"。{err_body[:200]}"
        return False, msg
    except Exception as e:
        return False, f"创建任务请求异常：{e!s}"

    try:
        data = json.loads(raw)
    except Exception:
        return False, f"创建任务返回非 JSON：{raw[:300]}"

    task_id_path = spec.get("task_id_path") or "data.task_id"
    task_id = _get_by_path(data, task_id_path)
    if not task_id or not isinstance(task_id, str):
        return False, data.get("message") or "创建成功但未返回 task_id"

    poll_url_template = (spec.get("poll_url_template") or "").strip()
    if not poll_url_template or "{{task_id}}" not in poll_url_template:
        return False, "execution.poll_url_template 未配置或缺少 {{task_id}}"
    poll_url = poll_url_template.replace("{{task_id}}", task_id)
    status_path = spec.get("status_path") or "data.task_status"
    success_list = [s.upper() for s in (spec.get("success_statuses") or ["COMPLETED", "SUCCESS"])]
    failure_list = [s.upper() for s in (spec.get("failure_statuses") or ["FAILED", "ERROR", "EXPIRED", "CANCELED", "PENDING"])]
    result_cfg = spec.get("result") or {}
    ppt_path = result_cfg.get("ppt_url") or "data.ppt_url"
    live_doc_path = result_cfg.get("live_doc_url") or "data.live_doc_url"
    err_path = result_cfg.get("error_message") or "data.error_message"
    poll_interval = max(2, min(30, int(spec.get("poll_interval") or 5)))
    max_wait = max(10, min(1800, int(spec.get("max_wait") or 600)))
    poll_timeout = min(60, timeout)

    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        req_poll = urllib.request.Request(poll_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req_poll, timeout=poll_timeout) as resp:
                poll_raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = ""
            return False, f"轮询任务状态失败（HTTP {e.code}）：{err_body[:200]}"
        except Exception as e:
            return False, f"轮询请求异常：{e!s}"

        try:
            poll_data = json.loads(poll_raw)
        except Exception:
            time.sleep(poll_interval)
            continue
        status = _get_by_path(poll_data, status_path)
        if isinstance(status, str):
            status_upper = status.upper()
            if status_upper in success_list:
                ppt_url = _get_by_path(poll_data, ppt_path)
                live_doc_url = _get_by_path(poll_data, live_doc_path)
                if isinstance(ppt_url, str) and ppt_url.strip():
                    out = f"## PPT 已生成\n\n**演示文稿链接：** [打开 PPT]({ppt_url})\n\n"
                    if isinstance(live_doc_url, str) and live_doc_url.strip():
                        out += f"**在线编辑链接：** [LiveDoc]({live_doc_url})\n\n"
                    return True, out.strip()
                if isinstance(live_doc_url, str) and live_doc_url.strip():
                    return True, f"## PPT 已生成\n\n**链接：** [打开]({live_doc_url})\n\n"
                return True, "任务已完成，但未返回 ppt_url / live_doc_url。"
            if status_upper in failure_list:
                err_msg = _get_by_path(poll_data, err_path) or "任务失败，未返回具体原因。"
                return False, f"PPT 任务失败（{status}）：{err_msg}"

        time.sleep(poll_interval)

    return False, f"轮询超时（{max_wait} 秒），未在限定时间内完成。"


def run_plan(spec: dict, prompt: str) -> tuple[bool, str]:
    """
    按 metadata.execution (type=plan) 执行：根据「理解 Skill 后生成的步骤」依次执行，不硬编码具体业务。
    spec.steps 中每步可为：
    - action: "http" — 单次请求，method/url/headers/body，extract: { "变量名": "data.path" } 写入上下文供后续步骤用
    - action: "poll" — 轮询 url（可含 {{变量名}}），status_path / success_values / failure_values / result / error_path，poll_interval / max_wait
    占位符：{{prompt}}、{{ENV:VAR}}、以及前序步骤 extract 的变量名（如 {{task_id}}）。
    """
    if (spec.get("type") or "").lower() != "plan":
        return False, "execution.type 非 plan，无法执行"

    steps = spec.get("steps")
    if not steps or not isinstance(steps, list):
        return False, "execution.steps 为空或非数组"

    # 初始上下文：prompt + 所有 ENV（供 {{ENV:VAR}} 与 {{prompt}} 替换）
    context: dict[str, str] = {"prompt": prompt or ""}
    for k, v in os.environ.items():
        context[f"ENV:{k}"] = (v or "").strip().strip("'\"")

    timeout = max(10, min(120, int(spec.get("timeout") or 60)))
    poll_timeout = min(60, timeout)

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        action = (step.get("action") or "").strip().lower()
        headers = _substitute_context(step.get("headers") or {}, context)
        if not isinstance(headers, dict):
            headers = {}
        headers["User-Agent"] = USER_AGENT

        if action == "http":
            method = (step.get("method") or "GET").upper()
            url = _substitute_context(step.get("url") or "", context)
            if not url.strip():
                return False, f"步骤 {i+1} (http) url 为空"
            body = None
            if method == "POST":
                body_obj = _substitute_context(step.get("body") or {}, context)
                if isinstance(body_obj, dict):
                    body = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
                    headers.setdefault("Content-Type", "application/json")
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                err_b = ""
                try:
                    err_b = e.read().decode("utf-8")
                except Exception:
                    pass
                try:
                    j = json.loads(err_b) if err_b.strip() else {}
                    msg = j.get("message") or j.get("error_message") or err_b[:200]
                except Exception:
                    msg = err_b[:200]
                return False, f"步骤 {i+1} 请求失败（HTTP {e.code}）：{msg}"
            except Exception as e:
                return False, f"步骤 {i+1} 请求异常：{e!s}"
            try:
                data = json.loads(raw)
            except Exception:
                return False, f"步骤 {i+1} 返回非 JSON"
            for var_name, path in (step.get("extract") or {}).items():
                val = _get_by_path(data, path)
                if val is not None:
                    context[var_name] = str(val).strip()

        elif action == "poll":
            url = _substitute_context(step.get("url") or "", context)
            if not url.strip():
                return False, f"步骤 {i+1} (poll) url 为空"
            status_path = step.get("status_path") or "data.task_status"
            success_list = [s.upper() for s in (step.get("success_values") or ["COMPLETED", "SUCCESS"])]
            failure_list = [s.upper() for s in (step.get("failure_values") or ["FAILED", "ERROR", "EXPIRED", "CANCELED", "PENDING"])]
            result_map = step.get("result") or {}
            error_path = step.get("error_path") or "data.error_message"
            poll_interval = max(2, min(30, int(step.get("poll_interval") or 5)))
            max_wait = max(10, min(1800, int(step.get("max_wait") or 600)))
            deadline = time.monotonic() + max_wait
            while time.monotonic() < deadline:
                req_poll = urllib.request.Request(url, headers=headers, method="GET")
                try:
                    with urllib.request.urlopen(req_poll, timeout=poll_timeout) as resp:
                        poll_raw = resp.read().decode("utf-8")
                except urllib.error.HTTPError as e:
                    try:
                        err_b = e.read().decode("utf-8")
                    except Exception:
                        err_b = ""
                    return False, f"步骤 {i+1} 轮询失败（HTTP {e.code}）：{err_b[:200]}"
                except Exception as e:
                    return False, f"步骤 {i+1} 轮询异常：{e!s}"
                try:
                    poll_data = json.loads(poll_raw)
                except Exception:
                    time.sleep(poll_interval)
                    continue
                status = _get_by_path(poll_data, status_path)
                if isinstance(status, str):
                    status_upper = status.upper()
                    if status_upper in success_list:
                        for var_name, path in result_map.items():
                            val = _get_by_path(poll_data, path)
                            if val is not None:
                                context[var_name] = str(val).strip()
                        # 使用 execution.response 的模板或默认格式输出
                        resp_cfg = spec.get("response") or {}
                        tpl = resp_cfg.get("success_template")
                        if isinstance(tpl, str) and tpl.strip():
                            out = _substitute_context(tpl, context)
                            return True, out.strip()
                        # 默认：若有 ppt_url / live_doc_url 则格式化
                        ppt_url = context.get("ppt_url", "").strip()
                        live_doc_url = context.get("live_doc_url", "").strip()
                        if ppt_url:
                            out = f"## 任务已完成\n\n**链接：** [打开]({ppt_url})\n\n"
                            if live_doc_url:
                                out += f"**在线编辑：** [LiveDoc]({live_doc_url})\n\n"
                            return True, out.strip()
                        if live_doc_url:
                            return True, f"## 任务已完成\n\n**链接：** [打开]({live_doc_url})\n\n"
                        return True, "任务已完成。"
                    if status_upper in failure_list:
                        err_msg = _get_by_path(poll_data, error_path) or "未返回具体原因"
                        return False, f"步骤 {i+1} 任务失败（{status}）：{err_msg}"
                time.sleep(poll_interval)
            return False, f"步骤 {i+1} 轮询超时（{max_wait} 秒）"

    # 全部为 http 且无 poll 时，用最后一步的响应或 response.success_template 格式化
    resp_cfg = spec.get("response") or {}
    tpl = resp_cfg.get("success_template")
    if isinstance(tpl, str) and tpl.strip():
        return True, _substitute_context(tpl, context).strip()
    return True, json.dumps(context, ensure_ascii=False, indent=2)
