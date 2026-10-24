"""Generate wbs/wbs-msp.xml: the MS Project view of the WBS.

The importer used in this lab derives task duration from Work + assignment;
a task with no Work and no assignment imports with duration 0 regardless of
its Start/Finish/Duration values.  This script therefore mirrors the known
good reference file: every task carries Work, and every leaf has exactly one
assignment.  Each leaf gets its own resource (used once), so the resource
calendar can never force a re-schedule.

The detailed plan (plan/tasks.csv) stays the source of truth for EVM and
actuals; this file is only for the MS Project screenshot.
"""

import datetime as dt
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pm_metrics as pm

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "wbs", "wbs-msp.xml")

# (phase, merged task name, member ids)
GROUPS = [
    ("1", "商业论证与项目章程", ["1.1", "1.2"]),
    ("1", "干系人登记与启动阶段评审", ["1.3", "1.4"]),
    ("1", "启动阶段收口与派单", ["1.5"]),
    ("2", "范围、需求与架构设计", ["2.1", "2.2", "2.3"]),
    ("2", "风险登记与质量计划", ["2.4"]),
    ("2", "进度计划与成本基线", ["2.5", "2.6"]),
    ("2", "甘特图与规划基线评审", ["2.7", "2.8"]),
    ("3", "WP1 账户与角色权限", ["3.1"]),
    ("3", "QA1 验证账户与权限", ["3.2"]),
    ("3", "WP2 设备目录与查询", ["3.3"]),
    ("3", "QA2 验证设备查询", ["3.4"]),
    ("3", "WP3 申请审批与冲突阻止", ["3.5"]),
    ("3", "QA3 验证审批与冲突阻止", ["3.6"]),
    ("3", "WP4 借出归还与逾期", ["3.7"]),
    ("3", "QA4 验证借还生命周期", ["3.8"]),
    ("3", "WP5 统计与审计日志", ["3.9"]),
    ("3", "QA5 验证统计与审计", ["3.10"]),
    ("3", "演示脚本与执行期集成", ["3.11", "3.12"]),
    ("4", "EVM 偏差分析与完工预测", ["4.1", "4.2"]),
    ("5", "验收演示、经验教训与归档移交", ["5.1", "5.2", "5.3"]),
]


def main():
    pm.load_rates(os.path.join(BASE, "plan", "rates.csv"))
    tasks, _ = pm.load_tasks(os.path.join(BASE, "plan", "tasks.csv"))

    gid_of = {}
    for i, (_, _, members) in enumerate(GROUPS):
        for m in members:
            gid_of[m] = "G%02d" % i

    merged, order = {}, []
    for i, (phase, name, members) in enumerate(GROUPS):
        gid = "G%02d" % i
        preds = []
        for m in members:
            for p in tasks[m]["preds"]:
                gp = gid_of[p]
                if gp != gid and gp not in preds:
                    preds.append(gp)
        duration = sum(tasks[m]["duration"] for m in members)
        if duration < 1:
            duration = 1.0
        roles = []
        for m in members:
            if tasks[m]["resource"] not in roles:
                roles.append(tasks[m]["resource"])
        merged[gid] = {
            "id": gid,
            "phase": phase,
            "name": name,
            "duration": round(duration, 4),
            "preds": preds,
            "roles": roles,
        }
        order.append(gid)
    for gid in order:
        merged[gid]["preds"] = [p for p in order if p in merged[gid]["preds"]]

    pm.cpm(merged, order)
    finish = max(t["ef"] for t in merged.values())

    start = dt.datetime(2026, 11, 2)
    root = ET.Element("Project", xmlns="http://schemas.microsoft.com/project")

    def sub(parent, tag, text):
        ET.SubElement(parent, tag).text = str(text)

    def dur_str(days):
        h = days * 8
        whole = int(round(h))
        if abs(h - whole) < 1e-9:
            return "PT%dH0M0S" % whole
        minutes = int(round((h - int(h)) * 60))
        return "PT%dH%dM0S" % (int(h), minutes)

    def dstr(d):
        return pm.fmt_date(start.date(), d).replace(" ", "T") + ":00"

    sub(root, "SaveVersion", 14)
    sub(root, "Name", "实验室设备借用管理系统（DeviceLoan MVP）")
    sub(root, "Title", "DeviceLoan MVP WBS (MS Project view)")
    sub(root, "Subject", "整日粒度 WBS，用于 MS Project 截图")
    sub(root, "Category", "课程实验")
    sub(root, "Company", "DeviceLoan 项目组")
    sub(root, "Manager", "PM")
    sub(root, "Author", "多智能体团队")
    sub(root, "CreationDate", "2026-11-02T08:00:00")
    sub(root, "LastSaved", "2026-11-02T08:00:00")
    sub(root, "ScheduleFromStart", 1)
    sub(root, "StartDate", "2026-11-02T08:00:00")
    sub(root, "FinishDate", dstr(finish))
    sub(root, "FYStartDate", 1)
    sub(root, "CriticalSlackLimit", 0)
    sub(root, "CurrencyDigits", 2)
    sub(root, "CurrencySymbol", "CNY")
    sub(root, "CurrencyCode", "CNY")
    sub(root, "CurrencySymbolPosition", 0)
    sub(root, "CalendarUID", 1)
    sub(root, "DefaultStartTime", "08:00:00")
    sub(root, "DefaultFinishTime", "17:00:00")
    sub(root, "MinutesPerDay", 480)
    sub(root, "MinutesPerWeek", 2400)
    sub(root, "DaysPerMonth", 20)
    sub(root, "DefaultTaskType", 1)
    sub(root, "DefaultFixedCostAccrual", 3)
    sub(root, "DefaultStandardRate", 0)
    sub(root, "DefaultOvertimeRate", 0)
    sub(root, "DurationFormat", 7)
    sub(root, "WorkFormat", 2)
    sub(root, "EditableActualCosts", 0)
    sub(root, "HonorConstraints", 1)
    sub(root, "InsertedProjectsLikeSummary", 0)
    sub(root, "MultipleCriticalPaths", 0)
    sub(root, "NewTasksEffortDriven", 0)
    sub(root, "NewTasksEstimated", 1)
    sub(root, "NewTasksAreManual", 0)
    sub(root, "SplitsInProgressTasks", 0)
    sub(root, "SpreadActualCost", 0)
    sub(root, "SpreadPercentComplete", 0)
    sub(root, "TaskUpdatesResource", 0)
    sub(root, "FiscalYearStart", 0)
    sub(root, "WeekStartDay", 1)
    sub(root, "NewTaskStartDate", 0)
    sub(root, "CurrentDate", "2026-11-02T08:00:00")
    sub(root, "Autolink", 1)

    cals = ET.SubElement(root, "Calendars")
    cal = ET.SubElement(cals, "Calendar")
    sub(cal, "UID", 1)
    sub(cal, "Name", "Standard")
    sub(cal, "IsBaseCalendar", 1)
    sub(cal, "BaseCalendarUID", -1)
    wds = ET.SubElement(cal, "WeekDays")
    for day in range(1, 8):
        wd = ET.SubElement(wds, "WeekDay")
        sub(wd, "DayType", day)
        working = day not in (1, 7)
        sub(wd, "DayWorking", 1 if working else 0)
        if working:
            wts = ET.SubElement(wd, "WorkingTimes")
            for frm, to in (("08:00:00", "12:00:00"), ("13:00:00", "17:00:00")):
                wt = ET.SubElement(wts, "WorkingTime")
                sub(wt, "FromTime", frm)
                sub(wt, "ToTime", to)

    tks = ET.SubElement(root, "Tasks")
    uid = 1
    uids = {}
    phases = []
    for gid in order:
        if merged[gid]["phase"] not in phases:
            phases.append(merged[gid]["phase"])

    for ph in phases:
        kids = [merged[g] for g in order if merged[g]["phase"] == ph]
        es = min(k["es"] for k in kids)
        ef = max(k["ef"] for k in kids)
        e = ET.SubElement(tks, "Task")
        sub(e, "UID", uid)
        sub(e, "ID", uid)
        sub(e, "Name", "%s %s" % (ph, pm.PHASE_NAMES.get(ph, "")))
        sub(e, "Type", 1)
        sub(e, "IsNull", 0)
        sub(e, "Active", 1)
        sub(e, "Manual", 0)
        sub(e, "CreateDate", "2026-11-02T08:00:00")
        sub(e, "WBS", ph)
        sub(e, "OutlineNumber", ph)
        sub(e, "OutlineLevel", 1)
        sub(e, "Priority", 500)
        sub(e, "Start", dstr(es))
        sub(e, "Finish", dstr(ef))
        sub(e, "Duration", dur_str(ef - es))
        sub(e, "DurationFormat", 7)
        sub(e, "ResumeValid", 0)
        sub(e, "EffortDriven", 0)
        sub(e, "Recurring", 0)
        sub(e, "OverAllocated", 0)
        sub(e, "Estimated", 0)
        sub(e, "Milestone", 0)
        sub(e, "Summary", 1)
        sub(e, "Critical", 1)
        sub(e, "IsSubproject", 0)
        sub(e, "ExternalTask", 0)
        sub(e, "EarlyStart", dstr(es))
        sub(e, "EarlyFinish", dstr(ef))
        sub(e, "LateStart", dstr(es))
        sub(e, "LateFinish", dstr(ef))
        uid += 1

        leaves = [g for g in order if merged[g]["phase"] == ph]
        for n, gid in enumerate(leaves, start=1):
            t = merged[gid]
            e = ET.SubElement(tks, "Task")
            sub(e, "UID", uid)
            sub(e, "ID", uid)
            sub(e, "Name", t["name"])
            sub(e, "Type", 1)
            sub(e, "IsNull", 0)
            sub(e, "Active", 1)
            sub(e, "Manual", 0)
            sub(e, "CreateDate", "2026-11-02T08:00:00")
            sub(e, "WBS", "%s.%d" % (ph, n))
            sub(e, "OutlineNumber", "%s.%d" % (ph, n))
            sub(e, "OutlineLevel", 2)
            sub(e, "Priority", 500)
            sub(e, "Start", dstr(t["es"]))
            sub(e, "Finish", dstr(t["ef"]))
            sub(e, "Duration", dur_str(t["duration"]))
            sub(e, "DurationFormat", 7)
            sub(e, "Work", dur_str(t["duration"]))
            sub(e, "ResumeValid", 0)
            sub(e, "EffortDriven", 0)
            sub(e, "Recurring", 0)
            sub(e, "OverAllocated", 0)
            sub(e, "Estimated", 0)
            sub(e, "Milestone", 0)
            sub(e, "Summary", 0)
            sub(e, "Critical", 1 if t["critical"] else 0)
            sub(e, "IsSubproject", 0)
            sub(e, "ExternalTask", 0)
            sub(e, "EarlyStart", dstr(t["es"]))
            sub(e, "EarlyFinish", dstr(t["ef"]))
            sub(e, "LateStart", dstr(t["ls"]))
            sub(e, "LateFinish", dstr(t["lf"]))
            sub(e, "ConstraintType", 4)
            sub(e, "ConstraintDate", dstr(t["es"]))
            sub(e, "Notes", "负责：%s" % "/".join(t["roles"]))
            for p in t["preds"]:
                link = ET.SubElement(e, "PredecessorLink")
                sub(link, "PredecessorUID", uids[p])
                sub(link, "Type", 1)
                sub(link, "CrossProject", 0)
                sub(link, "LinkLag", 0)
                sub(link, "LagFormat", 7)
            uids[gid] = uid
            uid += 1

    # one resource per leaf, used exactly once -> no over-allocation possible
    res = ET.SubElement(root, "Resources")
    for i, gid in enumerate(order, start=1):
        t = merged[gid]
        r = ET.SubElement(res, "Resource")
        sub(r, "UID", i)
        sub(r, "ID", i)
        sub(r, "Name", "%s-%s.%d" % (t["roles"][0], t["phase"],
                                     [g for g in order if merged[g]["phase"] == t["phase"]].index(gid) + 1))
        sub(r, "Type", 1)
        sub(r, "IsNull", 0)
        sub(r, "Initials", t["roles"][0])
        sub(r, "MaxUnits", 1)
        sub(r, "StandardRate", 0)
        sub(r, "StandardRateFormat", 2)
        sub(r, "OvertimeRate", 0)
        sub(r, "OvertimeRateFormat", 2)
        sub(r, "CostPerUse", 0)

    asg = ET.SubElement(root, "Assignments")
    for i, gid in enumerate(order, start=1):
        a = ET.SubElement(asg, "Assignment")
        sub(a, "UID", i)
        sub(a, "TaskUID", uids[gid])
        sub(a, "ResourceUID", i)
        sub(a, "Units", 1)
        sub(a, "PercentWorkComplete", 0)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tree.write(OUT, encoding="utf-8", xml_declaration=True)
    print("OUT=%s tasks=%d finish=%.2f" % (OUT, len(order) + len(phases), finish))


if __name__ == "__main__":
    main()
