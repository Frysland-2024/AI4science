from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from payload_contract import (
    PAYLOAD_CONTRACT_VERSION,PAYLOAD_MANIFEST_MEMBER,PAYLOAD_REQUIRED_FILES,
)
from verify_source_snapshot import read_and_validate_manifest,verify_extracted_tree


class SourceSnapshotTests(unittest.TestCase):
    def make_archive(self,root,*,version=PAYLOAD_CONTRACT_VERSION,corrupt=False,extra=None):
        archive=Path(root)/"source_snapshot.zip"
        members={name:("source:"+name).encode() for name in PAYLOAD_REQUIRED_FILES}
        files={name:hashlib.sha256(data).hexdigest() for name,data in members.items()}
        manifest={
            "schema":"pxrd-v11-source-snapshot-v1",
            "contract_version":version,
            "required_files":list(PAYLOAD_REQUIRED_FILES),
            "files":files,
            "source_git_commit":"deadbeef",
        }
        if extra is not None:
            members[extra]=b"unexpected"
        with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for name,data in members.items():
                zf.writestr(name,b"altered" if corrupt and name==PAYLOAD_REQUIRED_FILES[0] else data)
            zf.writestr(PAYLOAD_MANIFEST_MEMBER,json.dumps(manifest).encode())
        return archive,members,manifest

    def test_manifest_and_extracted_tree_hashes_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            archive,members,expected=self.make_archive(temp)
            actual=read_and_validate_manifest(archive)
            self.assertEqual(actual,expected)
            root=Path(temp)/"extracted"
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(root)
            verify_extracted_tree(actual,root/"AI4science")

    def test_stale_version_and_member_hash_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            stale,_,_=self.make_archive(temp,version="old-v11-snapshot")
            with self.assertRaisesRegex(ValueError,"stale or unsupported"):
                read_and_validate_manifest(stale)
            corrupted,_,_=self.make_archive(temp,corrupt=True)
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                read_and_validate_manifest(corrupted)

    def test_unmanifested_and_unsafe_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            extra,_,_=self.make_archive(temp,extra="AI4science/extra.py")
            with self.assertRaisesRegex(ValueError,"unmanifested or missing"):
                read_and_validate_manifest(extra)
            unsafe,_,_=self.make_archive(temp,extra="AI4science/../outside.py")
            with self.assertRaisesRegex(ValueError,"unsafe ZIP member"):
                read_and_validate_manifest(unsafe)


if __name__=="__main__":
    unittest.main()
