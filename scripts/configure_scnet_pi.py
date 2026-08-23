#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 SCNet（https://www.scnet.cn）模型 API 配置为 pi 的一个 provider（scnet）。

用法:
    python3 scripts/configure_scnet_pi.py --key "<API_KEY>"

行为:
  1. 用 key 调 SCNet /models 获取全部可用模型
  2. 在 ~/.pi/agent/models.json 的 providers 增补 scnet（OpenAI 协议，与 llama-local 同层）
  3. 清理 ~/.pi/agent/models-store.json 中的 scnet 残留
  4. 在 ~/.pi/agent/auth.json 写入 scnet 的 api_key
  不修改 zai-coding-cn / deepseek / anthropic / llama-local，不切换默认 provider。
"""
import argparse
import json
import urllib.request
from pathlib import Path

SCNET_BASE = "https://api.scnet.cn/api/llm/v1"
AGENT_DIR = Path.home() / ".pi" / "agent"
MODELS_JSON = AGENT_DIR / "models.json"
MODELS_STORE = AGENT_DIR / "models-store.json"
AUTH_JSON = AGENT_DIR / "auth.json"

# Token Plan 套餐内支持的模型（OpenAI 协议 id，来自平台「支持的模型」）
TOKEN_PLAN_MODELS = [
    "Kimi-K3", "Kimi-K2.5", "Kimi-K2.7-Code", "Kimi-K2.6",
    "DeepSeek-V4-Flash-0731", "DeepSeek-V4-Pro", "DeepSeek-V4-Flash",
    "Qwen3.8-Max",
    "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.5",
    "GLM-5.2", "GLM-5", "GLM-5.1",
]


def scnet_list_models(key: str) -> list[str]:
    req = urllib.request.Request(
        f"{SCNET_BASE}/models",
        headers={"Accept": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return [m["id"] for m in data.get("data", [])]


def build_scnet_models(names: list[str]) -> list[dict]:
    models = []
    for mid in names:
        models.append({
            "id": mid,
            "name": mid,
            "reasoning": False,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 128000,
            "maxTokens": 32768,
        })
    return models


def run(key: str, model_ids: list[str] | None = None):
    if model_ids:
        models = model_ids
    else:
        models = scnet_list_models(key)
        print(f"从 SCNet /models 获取到 {len(models)} 个模型")
    print(f"配置 {len(models)} 个模型：{models}")

    # 1) auth.json：写入 scnet key
    auth = json.loads(AUTH_JSON.read_text()) if AUTH_JSON.exists() else {}
    auth["scnet"] = {"type": "api_key", "key": key}
    AUTH_JSON.write_text(json.dumps(auth, ensure_ascii=False, indent=2))
    print("已写入 auth.json: scnet")

    # 2) models.json：providers 增补 scnet（与 llama-local 同层）
    cfg = json.loads(MODELS_JSON.read_text()) if MODELS_JSON.exists() else {}
    cfg.setdefault("providers", {})["scnet"] = {
        "baseUrl": SCNET_BASE,
        "api": "openai-completions",
        "apiKey": key,
        "compat": {
            "supportsDeveloperRole": False,
            "supportsReasoningEffort": False,
        },
        "models": build_scnet_models(models),
    }
    MODELS_JSON.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    print("已写入 models.json: providers.scnet（%d 个模型）" % len(models))

    # 3) models-store.json：清理 scnet 残留（它是远程 catalog 缓存，不属于手动 provider）
    if MODELS_STORE.exists():
        store = json.loads(MODELS_STORE.read_text())
        if "scnet" in store:
            del store["scnet"]
            MODELS_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2))
            print("已从 models-store.json 移除 scnet（远程缓存区）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="SCNet Token Plan 专属 API Key（sk-tp- 开头，请填完整未打码值）")
    ap.add_argument("--models", default="", help="逗号分隔模型 id 列表；留空则用 Token Plan 套餐支持模型白名单")
    args = ap.parse_args()
    model_ids = [m.strip() for m in args.models.split(",") if m.strip()] if args.models else TOKEN_PLAN_MODELS
    run(args.key, model_ids or None)
