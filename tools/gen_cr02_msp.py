"""Generate wbs/wbs-cr02-msp.xml: the MS Project view of the phase-2 increment.

This mirrors the known-good structure of tools/gen_msp_wbs.py (Manual=0 after
Active, Work on every leaf, one resource per leaf, ConstraintType/Date), but
only contains the 5 CR-02 tasks.  Phase 1 remains in wbs/wbs-msp.xml and is
not modified.
"""

import datetime as dt
import os
import sys
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pm_metrics as pm

OUT = os.path.join(BASE, "wbs", "wbs-cr02-msp.xml")
TASKS = os.path.join(BASE, "plan", "tasks-cr02.csv")
START = dt.datetime(2026, 11, 30)
STAMP = "2026-11-30T08:00:00"


def dur_str(days):
    h = days * 8
    whole = int(round(h))
    if abs(h - whole) < 1e-9:
        return "PT%dH0M0S" % whole
    minutes = int(round((h - int(h)) * 60))
    return "PT%dH%dM0S" % (int(h), minutes)


def dstr(d):
    return pm.fmt_date(START.date(), d).replace(" ", "T") + ":00"


def sub(parent, tag, text):
    ET.SubElement(parent, tag).text = str(text)


def main():
    pm.load_rates(os.path.join(BASE, "plan", "rates.csv"))
    tasks, order = pm.load_tasks(TASKS)
    pm.cpm(tasks, order)
    finish = max(t["ef"] for t in tasks.values())
    roles = sorted(pm.RATES)
    res_uid = {role: i for i, role in enumerate(roles, start=1)}

    root = ET.Element("Project", xmlns="http://schemas.microsoft.com/project")

    def header(tag, val):
        sub(root, tag, val)

    header("SaveVersion", 14)
    header("Name", "实验室设备借用管理系统（二期 CR-02 候补队列）")
    header("Title", "DeviceLoan MVP 二期 WBS (MS Project view)")
    header("Subject", "CR-02 候补队列：验收后增量，2.5 天")
    header("Category", "课程实验")
    header("Company", "DeviceLoan 项目组")
    header("Manager", "PM")
    header("Author", "多智能体团队")
    header("CreationDate", STAMP)
    header("LastSaved", STAMP)
    header("ScheduleFromStart", 1)
    header("StartDate", STAMP)
    header("FinishDate", dstr(finish))
    header("FYStartDate", 1)
    header("CriticalSlackLimit", 0)
    header("CurrencyDigits", 2)
    header("CurrencySymbol", "CNY")
    header("CurrencyCode", "CNY")
    header("CurrencySymbolPosition", 0)
    header("CalendarUID", 1)
    header("DefaultStartTime", "08:00:00")
    header("DefaultFinishTime", "17:00:00")
    header("MinutesPerDay", 480)
    header("MinutesPerWeek", 2400)
    header("DaysPerMonth", 20)
    header("DefaultTaskType", 1)
    header("DefaultFixedCostAccrual", 3)
    header("DefaultStandardRate", 0)
    header("DefaultOvertimeRate", 0)
    header("DurationFormat", 7)
    header("WorkFormat", 2)
    header("EditableActualCosts", 0)
    header("HonorConstraints", 1)
    header("InsertedProjectsLikeSummary", 0)
    header("MultipleCriticalPaths", 0)
    header("NewTasksEffortDriven", 0)
    header("NewTasksEstimated", 1)
    header("NewTasksAreManual", 0)
    header("SplitsInProgressTasks", 0)
    header("SpreadActualCost", 0)
    header("SpreadPercentComplete", 0)
    header("TaskUpdatesResource", 0)
    header("FiscalYearStart", 0)
    header("WeekStartDay", 1)
    header("NewTaskStartDate", 0)
    header("CurrentDate", STAMP)
    header("Autolink", 1)

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
    uids = {}

    # summary row: 6 二期 CR-02
    es = 0.0
    ef = finish
    e = ET.SubElement(tks, "Task")
    sub(e, "UID", 1)
    sub(e, "ID", 1)
    sub(e, "Name", "6 二期 CR-02")
    sub(e, "Active", 1)
    sub(e, "Manual", 0)
    sub(e, "Type", 1)
    sub(e, "IsNull", 0)
    sub(e, "CreateDate", STAMP)
    sub(e, "WBS", "6")
    sub(e, "OutlineNumber", "6")
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

    for n, tid in enumerate(order, start=2):
        t = tasks[tid]
        e = ET.SubElement(tks, "Task")
        sub(e, "UID", n)
        sub(e, "ID", n)
        sub(e, "Name", t["name"])
        sub(e, "Active", 1)
        sub(e, "Manual", 0)
        sub(e, "Type", 1)
        sub(e, "IsNull", 0)
        sub(e, "CreateDate", STAMP)
        sub(e, "WBS", tid)
        sub(e, "OutlineNumber", tid)
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
        sub(e, "Notes", "负责：%s；计划 %.2f 人日" % (t["resource"], t["person_days"]))
        for p in t["preds"]:
            link = ET.SubElement(e, "PredecessorLink")
            sub(link, "PredecessorUID", uids[p])
            sub(link, "Type", 1)
            sub(link, "CrossProject", 0)
            sub(link, "LinkLag", 0)
            sub(link, "LagFormat", 7)
        uids[tid] = n

    res = ET.SubElement(root, "Resources")
    for i, tid in enumerate(order, start=1):
        t = tasks[tid]
        r = ET.SubElement(res, "Resource")
        sub(r, "UID", i)
        sub(r, "ID", i)
        sub(r, "Name", "%s-%s" % (t["resource"], tid))
        sub(r, "Type", 1)
        sub(r, "IsNull", 0)
        sub(r, "Initials", t["resource"])
        sub(r, "MaxUnits", 1)
        sub(r, "StandardRate", 0)
        sub(r, "StandardRateFormat", 2)
        sub(r, "OvertimeRate", 0)
        sub(r, "OvertimeRateFormat", 2)
        sub(r, "CostPerUse", 0)
        sub(r, "CalendarUID", 1)

    asg = ET.SubElement(root, "Assignments")
    for i, tid in enumerate(order, start=1):
        a = ET.SubElement(asg, "Assignment")
        sub(a, "UID", i)
        sub(a, "TaskUID", uids[tid])
        sub(a, "ResourceUID", i)
        sub(a, "Units", 1)
        sub(a, "PercentWorkComplete", 0)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tree.write(OUT, encoding="utf-8", xml_declaration=True)
    print("OUT=%s tasks=%d finish=%.2f" % (OUT, len(order) + 1, finish))


if __name__ == "__main__":
    main()
