"""Merge phase-1 and phase-2 WBS XML into one MS Project file.

Input:
  wbs/wbs-msp.xml      phase 1, 20 leaves, 19.75 days
  wbs/wbs-cr02-msp.xml phase 2, 5 leaves, 2.5 days (starts 2026-11-30)
Output:
  wbs/wbs-all-msp.xml  combined view; phase-1 rows are unchanged, phase-2
                       rows are appended with offset UIDs.
"""

import os
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "http://schemas.microsoft.com/project"
OUT = os.path.join(BASE, "wbs", "wbs-all-msp.xml")
P1 = os.path.join(BASE, "wbs", "wbs-msp.xml")
P2 = os.path.join(BASE, "wbs", "wbs-cr02-msp.xml")


def tag(name):
    return "{%s}%s" % (NS, name)


def max_uid(parent, child_tag):
    vals = [int(e.findtext(tag("UID"))) for e in parent.findall(tag(child_tag))]
    return max(vals) if vals else 0


def main():
    ET.register_namespace("", NS)
    t1 = ET.parse(P1)
    r1 = t1.getroot()
    t2 = ET.parse(P2)
    r2 = t2.getroot()

    tasks1 = r1.find(tag("Tasks"))
    tasks2 = r2.find(tag("Tasks"))
    res1 = r1.find(tag("Resources"))
    res2 = r2.find(tag("Resources"))
    asg1 = r1.find(tag("Assignments"))
    asg2 = r2.find(tag("Assignments"))

    task_off = max_uid(tasks1, "Task")
    res_off = max_uid(res1, "Resource")
    asg_off = max_uid(asg1, "Assignment")

    for e in tasks2.findall(tag("Task")):
        uid = int(e.findtext(tag("UID")))
        e.find(tag("UID")).text = str(uid + task_off)
        e.find(tag("ID")).text = str(uid + task_off)
        for link in e.findall(tag("PredecessorLink")):
            p = int(link.findtext(tag("PredecessorUID")))
            link.find(tag("PredecessorUID")).text = str(p + task_off)
        tasks1.append(e)

    for e in res2.findall(tag("Resource")):
        uid = int(e.findtext(tag("UID")))
        e.find(tag("UID")).text = str(uid + res_off)
        e.find(tag("ID")).text = str(uid + res_off)
        res1.append(e)

    for e in asg2.findall(tag("Assignment")):
        uid = int(e.findtext(tag("UID")))
        e.find(tag("UID")).text = str(uid + asg_off)
        e.find(tag("TaskUID")).text = str(int(e.findtext(tag("TaskUID"))) + task_off)
        e.find(tag("ResourceUID")).text = str(int(e.findtext(tag("ResourceUID"))) + res_off)
        asg1.append(e)

    r1.find(tag("Name")).text = "实验室设备借用管理系统（一期 + 二期 CR-02）"
    r1.find(tag("Title")).text = "DeviceLoan MVP 一期 + 二期 WBS"
    r1.find(tag("Subject")).text = "一期 19.75 天 + 二期 CR-02 2.5 天（验收后增量）"
    r1.find(tag("FinishDate")).text = "2026-12-02T12:00:00"
    r1.find(tag("CurrentDate")).text = "2026-11-30T08:00:00"
    r1.find(tag("LastSaved")).text = "2026-11-30T08:00:00"

    tree = ET.ElementTree(r1)
    ET.indent(tree, space="  ")
    tree.write(OUT, encoding="utf-8", xml_declaration=True)
    print("OUT=%s tasks=%d resources=%d assignments=%d" % (
        OUT,
        len(tasks1.findall(tag("Task"))),
        len(res1.findall(tag("Resource"))),
        len(asg1.findall(tag("Assignment"))),
    ))


if __name__ == "__main__":
    main()
