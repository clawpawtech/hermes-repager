"""Spawn-safe unit-test runner with a machine-readable receipt (no model calls)."""
import argparse
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(ROOT))
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    receipt={'tests':result.testsRun,'skipped':len(result.skipped),'failures':len(result.failures),
             'errors':len(result.errors),'success':result.wasSuccessful(),
             'skipped_tests':[str(test) for test,_reason in result.skipped]}
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    raise SystemExit(not result.wasSuccessful())

if __name__=='__main__':
    main()
