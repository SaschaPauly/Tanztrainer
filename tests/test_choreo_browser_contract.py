"""Run the same normative positive/negative Python mutations against JavaScript."""
import json
from pathlib import Path
import subprocess
import unittest
import test_choreo as contract


def javascript_validate(path, *, limits=None):
    command=['node',str(Path(__file__).with_name('choreo-runner.cjs')),str(path),json.dumps(limits or {})]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',check=True,timeout=20)
    response=json.loads(result.stdout)
    if 'error' in response:raise contract.ValidationError(response['error'])
    return response['manifest']


class BrowserContractTests(contract.ChoreoTests):
    def reject(self,pattern,**kwargs):
        # Different bounded readers may reject a hostile ZIP at an earlier
        # valid guard. Acceptance/rejection is the language-neutral contract.
        with self.assertRaises(contract.ValidationError):javascript_validate(self.write(**kwargs))

    @classmethod
    def setUpClass(cls):
        cls.original=contract.validate
        contract.validate=javascript_validate

    @classmethod
    def tearDownClass(cls):contract.validate=cls.original


if __name__=='__main__':unittest.main()
