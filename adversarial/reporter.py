import json
import dataclasses
from communication import Weakness, AttackReport, BuilderPatch


def report_to_json(report: AttackReport) -> str:
    return json.dumps(dataclasses.asdict(report))


def report_from_json(s: str) -> AttackReport:
    data = json.loads(s)
    data["weaknesses"] = [Weakness(**w) for w in data["weaknesses"]]
    return AttackReport(**data)


def patch_to_json(patch: BuilderPatch) -> str:
    return json.dumps(dataclasses.asdict(patch))


def patch_from_json(s: str) -> BuilderPatch:
    return BuilderPatch(**json.loads(s))
