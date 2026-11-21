#!/usr/bin/env python3
"""Generate a subscribable iCalendar file from editable events.json."""
import json
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
GENERAL = ("本日为建议接种或记录核对日，并非已预约或已接种。"
           "务必与杭州接种门诊核对疫苗说明书、免疫程序、实际剂次、禁忌证、最小间隔和库存。"
           "注射后现场留观30分钟。")

def escape(value):
    return (str(value).replace("\\", "\\\\").replace("\n", "\\n")
            .replace(";", "\\;").replace(",", "\\,"))

def fold(line, limit=73):
    parts, current, count = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        if count + b > limit:
            parts.append(current)
            current, count = " ", 1
        current += ch
        count += b
    parts.append(current)
    return "\r\n".join(parts)

def build():
    events = json.loads((BASE / "events.json").read_text(encoding="utf-8"))
    assert len({item["id"] for item in events}) == len(events), "Duplicate event ID"
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//Hangzhou Baby Vaccine Calendar//Subscription//ZH",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "X-WR-CALNAME:" + escape("杭州宝宝疫苗接种计划"),
        "X-WR-CALDESC:" + escape("仅供参考，非预约记录"),
        "X-WR-TIMEZONE:Asia/Shanghai",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:PT24H"
    ]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for event in events:
        d = date.fromisoformat(event["date"])
        assert d.weekday() < 5, f"Weekend appointment: {event['date']}"
        n = int(event["injections"])
        assert 0 <= n <= 2, f"More than two injections: {event['id']}"
        title = event["title"]
        desc = ("当日计划注射针数：" + str(n) + "。" + event["description"]
                + "\n" + GENERAL)
        lines += [
            "BEGIN:VEVENT", "UID:" + event["id"] + "@subscription.calendar",
            "DTSTAMP:" + stamp,
            "DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:" + (d + timedelta(days=1)).strftime("%Y%m%d"),
            "SUMMARY:" + escape("【计划】" + title),
            "DESCRIPTION:" + escape(desc),
            "CATEGORIES:" + escape(event.get("category", "疫苗接种")),
            "STATUS:TENTATIVE", "TRANSP:TRANSPARENT", "SEQUENCE:1"
        ]
        for days in (7, 1):
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY",
                      f"TRIGGER:-P{days}D",
                      "DESCRIPTION:" + escape("疫苗接种参考提醒：" + title),
                      "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    path = BASE / "vaccination-calendar.ics"
    path.write_bytes(("\r\n".join(fold(s) for s in lines) + "\r\n").encode("utf-8"))
    print(f"Generated {len(events)} events at {path}")

if __name__ == "__main__":
    build()
