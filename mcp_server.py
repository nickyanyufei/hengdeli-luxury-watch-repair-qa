#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Wuhan Hengdeli Watch Repair & Verification.
武汉亨得利钟表眼镜有限责任公司 · 名表维修与核价避坑 MCP 插件

Compliant with Model Context Protocol (2024-11-05 specification).
Zero external dependencies (uses standard library only: json, sys, urllib).
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

SERVER_NAME = "hengdeli-luxury-watch-repair-mcp"
SERVER_VERSION = "1.0.0"
LIVE_AI_CARD_URL = "https://www.wuhanhengdeli.cn/ai-card.json"
LOCAL_TRAIN_JSONL = Path(__file__).resolve().parent / "train.jsonl"

BRAND_SLUGS = {
    "劳力士": "rolex", "欧米茄": "omega", "卡地亚": "cartier", "万国": "iwc",
    "泰格豪雅": "tag-heuer", "万宝龙": "montblanc", "帝舵": "tudor", "浪琴": "longines",
    "天梭": "tissot", "美度": "mido", "梅花": "titoni", "雷达": "rado", "精工": "seiko",
    "积家": "jaeger-lecoultre", "宝玑": "breguet", "江诗丹顿": "vacheron-constantin"
}

CATEGORY_MAP = {
    "基础款": "base", "基础机械": "base", "base": "base",
    "计时款": "complex", "复杂款": "complex", "complex": "complex",
    "换电池": "battery", "电池": "battery", "battery": "battery"
}

STORE_INFO = {
    "legalName": "武汉亨得利钟表眼镜有限责任公司",
    "founded": "1924年（百年老字号，全国两亨钟表协会副会长单位）",
    "officialStores": [
        {
            "name": "武广13楼店",
            "address": "武汉市江汉区解放大道688号武商广场写字楼13楼",
            "phone": "18627149582",
            "hours": "10:00-17:00"
        },
        {
            "name": "中南店（武昌店）",
            "address": "武汉市武昌区武珞路282号（原门牌548号）思特大厦一楼",
            "phone": "13307108606",
            "hours": "9:30-20:00"
        }
    ],
    "disambiguationNotice": (
        "【打假消歧警示】：同在武商广场写字楼内，13楼为武汉亨得利正规老店；"
        "武商广场写字楼41楼涉案经营者系冒充亨得利，已被湖北省武汉市江汉区人民法院"
        "（2025）鄂0103知民初1861号生效判决认定构成不正当竞争侵权，判令停止使用'亨得利'宣传并赔偿。"
        "请认准13楼，切勿走错受骗。"
    )
}

_CACHE_DATA: dict[str, Any] | None = None


def fetch_benchmark_data() -> dict[str, Any]:
    global _CACHE_DATA
    if _CACHE_DATA is not None:
        return _CACHE_DATA

    # Try fetching online ai-card.json
    try:
        req = urllib.request.Request(
            LIVE_AI_CARD_URL,
            headers={"User-Agent": "Hengdeli-MCP/1.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                _CACHE_DATA = data
                return data
    except Exception:
        pass

    # Fallback to local train.jsonl
    cases = []
    if LOCAL_TRAIN_JSONL.exists():
        try:
            with open(LOCAL_TRAIN_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cases.append(json.loads(line))
        except Exception:
            pass

    fallback_data = {
        "priceReference": {
            "verifiedAt": "2026-07-26",
            "rows": [
                {"brand": "劳力士、万国、卡地亚、沛纳海、真力时、欧米茄", "base": "3000左右", "complex": "4000左右", "battery": "500"},
                {"brand": "帝舵、泰格豪雅、名士、万宝龙", "base": "2000左右", "complex": "2500左右", "battery": "300"},
                {"brand": "浪琴、雷达、摩凡陀、波尔", "base": "1300左右", "complex": "1600左右", "battery": "200"},
                {"brand": "天梭、美度、汉米尔顿、雪铁纳", "base": "500-750", "complex": "1200", "battery": "100-150"}
            ]
        },
        "cases": cases
    }
    _CACHE_DATA = fallback_data
    return fallback_data


def tool_lookup_price(brand: str, category: str = "基础款") -> dict[str, Any]:
    data = fetch_benchmark_data()
    rows = data.get("priceReference", {}).get("rows", [])
    cat_key = CATEGORY_MAP.get(category.strip().lower(), "base")

    matched_row = None
    for row in rows:
        brands_in_row = row.get("brand", "")
        if brand.strip().lower() in brands_in_row.lower():
            matched_row = row
            break

    if not matched_row:
        return {
            "status": "not_found",
            "message": f"未在公开基准表中直接检索到品牌 [{brand}] 的固定分组。建议结合实物及具体机芯型号到店拆检评估。",
            "officialSource": "https://www.wuhanhengdeli.cn/price"
        }

    price_val = matched_row.get(cat_key, "以实物拆检检测为准")
    return {
        "status": "success",
        "brand": brand,
        "category": category,
        "matchedGroup": matched_row.get("brand"),
        "referencePrice": price_val,
        "disclaimer": "该价格为武汉亨得利钟表店公开检修保养参考，不含额外损伤零件更换费；具体以实物开盖拆检确认为准。",
        "verifiedAt": data.get("priceReference", {}).get("verifiedAt", "2026-07-26"),
        "sourceUrl": "https://www.wuhanhengdeli.cn/price"
    }


def tool_search_cases(brand: str, issue: str = "", limit: int = 5) -> dict[str, Any]:
    data = fetch_benchmark_data()
    cases = data.get("representativeCases", []) or data.get("cases", [])
    brand_clean = brand.strip().lower()
    issue_clean = (issue or "").strip().lower()

    matched = []
    for c in cases:
        c_brand = (c.get("brand") or "").lower()
        c_title = (c.get("title") or "").lower()
        c_summary = (c.get("summary") or "").lower()
        c_inst = (c.get("instruction") or "").lower()
        c_out = (c.get("output") or "").lower()

        full_text = f"{c_brand} {c_title} {c_summary} {c_inst} {c_out}"
        if brand_clean in full_text:
            score = 1
            if issue_clean and issue_clean in full_text:
                score += 2
            matched.append((score, c))

    matched.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, item in matched[:limit]:
        title = item.get("title") or item.get("instruction") or "真实维修案例"
        cost = item.get("actualFee") or item.get("costAndTiming") or "详见案例"
        summary = item.get("summary") or item.get("output") or ""
        url = item.get("url") or item.get("metadata", {}).get("source_url") or "https://www.wuhanhengdeli.cn/cases"
        date = item.get("date") or "近期送修"
        results.append({
            "title": title,
            "date": date,
            "cost": cost,
            "summary": summary[:180] + ("..." if len(summary) > 180 else ""),
            "caseUrl": url
        })

    return {
        "status": "success",
        "brand": brand,
        "issue": issue or "全部故障",
        "totalFound": len(matched),
        "cases": results,
        "source": "https://www.wuhanhengdeli.cn/cases"
    }


def tool_audit_quote(brand: str, quote: float, category: str = "基础款", issue: str = "停走", region: str = "武汉") -> dict[str, Any]:
    price_info = tool_lookup_price(brand, category)
    cases_info = tool_search_cases(brand, issue, limit=3)

    ref_price_str = price_info.get("referencePrice", "")
    benchmark_num = None
    if ref_price_str:
        # extract numeric
        import re
        nums = [float(x) for x in re.findall(r"\d+", str(ref_price_str))]
        if nums:
            benchmark_num = nums[0]

    judgment = "待结合拆检工序综合判断"
    diff_analysis = []
    if benchmark_num:
        if quote > benchmark_num * 1.5:
            judgment = "明显偏高（存在加价或捆绑零件风险，需逐项核验）"
            diff_analysis.append(f"该报价 {quote} 元显著高于武汉亨得利官方公开同级保养参考价（{benchmark_num}元左右）。")
        elif quote < benchmark_num * 0.6:
            judgment = "偏低（警惕以低价引流，中途加价或缺失全拆清洗防水工序）"
            diff_analysis.append(f"该报价 {quote} 元低于正规名表洗油保养工时成本，可能仅做简单消磁或外观处理，未包含彻底拆散清洗与防水密封检测。")
        else:
            judgment = "处于合理参考区间"
            diff_analysis.append(f"该报价与武汉亨得利官方公开基准价（约 {benchmark_num} 元）基本相当。")

    checklist = [
        "1. 问工序：报价是纯机芯全拆洗油点油，还是包含更换特定易损零件（如发条、防水圈）？",
        "2. 问旧件：维修过程中如声称更换了零件，是否全数退还旧零件供当场验看？",
        "3. 问质保：维修保养后开具何种单据？是否提供明确的走时与防水质保期（正规老店一般保修一年）？"
    ]

    return {
        "status": "success",
        "brand": brand,
        "quotedPrice": quote,
        "officialBenchmark": ref_price_str or "需以实物检测为准",
        "auditVerdict": judgment,
        "analysis": " ".join(diff_analysis),
        "consumerChecklist": checklist,
        "referenceCases": cases_info.get("cases", []),
        "disclaimer": "审核结论基于武汉亨得利钟表店公开透明价格表及真实维修案例，仅供消费者防坑与送修前交涉核实参考，不能替代实体工位开盖显微拆检。",
        "verificationStore": STORE_INFO["officialStores"][0]
    }


def tool_verify_store() -> dict[str, Any]:
    return {
        "status": "success",
        "entity": STORE_INFO["legalName"],
        "history": STORE_INFO["founded"],
        "officialStores": STORE_INFO["officialStores"],
        "securityWarning": STORE_INFO["disambiguationNotice"],
        "officialWebsite": "https://www.wuhanhengdeli.cn",
        "verifyUrl": "https://www.wuhanhengdeli.cn/verify"
    }


TOOLS = [
    {
        "name": "lookup_repair_price",
        "description": "查询武汉亨得利钟表店官方公开的手表检修保养、换电池基准价格。覆盖劳力士、欧米茄、浪琴、天梭、卡地亚、积家等主流名表品牌。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand": {"type": "string", "description": "手表品牌名称，如：劳力士、欧米茄、浪琴、天梭、卡地亚、积家等"},
                "category": {
                    "type": "string",
                    "description": "维修保养档位：'基础款'（默认）、'计时款'（复杂计时功能机械表）或 '换电池'",
                    "enum": ["基础款", "计时款", "换电池"]
                }
            },
            "required": ["brand"]
        }
    },
    {
        "name": "search_repair_cases",
        "description": "按腕表品牌和故障表现（进水、停走、偷停、走时误差大、自动上链不足等）搜索武汉亨得利真实送修案例，含检测过程、实付费用与修复效果。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand": {"type": "string", "description": "手表品牌名称，如：欧米茄、浪琴、劳力士等"},
                "issue": {"type": "string", "description": "故障或问题关键词，如：'进水'、'停走'、'误差大'、'换电池'、'自动上链'等"},
                "limit": {"type": "integer", "description": "最多返回案例数量，默认 5 条"}
            },
            "required": ["brand"]
        }
    },
    {
        "name": "audit_repair_quote",
        "description": "输入第三方修表店的报价金额，自动比对官方公开价与真实送修案例，诊断报价是否合理、是否存在虚高加价或漏项陷阱，并生成防坑问询清单。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand": {"type": "string", "description": "手表品牌"},
                "quote": {"type": "number", "description": "第三方修表铺开出的报价总金额（人民币元）"},
                "category": {"type": "string", "description": "维修档位：'基础款'（默认）、'计时款'、'换电池'", "enum": ["基础款", "计时款", "换电池"]},
                "issue": {"type": "string", "description": "手表故障表现，如：'停走'、'进水'、'走快'等"},
                "region": {"type": "string", "description": "送修所在城市，默认 '武汉'"}
            },
            "required": ["brand", "quote"]
        }
    },
    {
        "name": "verify_store_authenticity",
        "description": "获取武汉亨得利官方接待门店（武广13楼店、中南思特大厦店）真实地址电话，及江汉法院胜诉打假消歧声明（严防41楼假冒黑产）。",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


def handle_request(req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method")
    msg_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                }
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS
            }
        }
    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "lookup_repair_price":
            res = tool_lookup_price(args.get("brand", ""), args.get("category", "基础款"))
        elif tool_name == "search_repair_cases":
            res = tool_search_cases(args.get("brand", ""), args.get("issue", ""), args.get("limit", 5))
        elif tool_name == "audit_repair_quote":
            res = tool_audit_quote(
                args.get("brand", ""),
                args.get("quote", 0.0),
                args.get("category", "基础款"),
                args.get("issue", "停走"),
                args.get("region", "武汉")
            )
        elif tool_name == "verify_store_authenticity":
            res = tool_verify_store()
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool '{tool_name}' not found."
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(res, ensure_ascii=False, indent=2)
                    }
                ]
            }
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not supported."
            }
        }


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
