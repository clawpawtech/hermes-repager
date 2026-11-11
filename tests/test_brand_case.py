"""Brand copy is lowercase; identifiers and captured source evidence stay exact."""
import re
import unittest
from pathlib import Path

class BrandCaseTests(unittest.TestCase):
    def test_public_copy_uses_lowercase_brand(self):
        root = Path(__file__).resolve().parents[1]
        files = [root/n for n in ('README.md','AGENTS.md','plugin.yaml','package.json','__init__.py')]
        for folder, suffixes in [('repager',{'.py','.mjs'}),('scripts',{'.py','.mjs'}),('docs',{'.md','.yaml'}),('skills',{'.md'}),('dashboard',{'.js','.json','.html','.svg'})]:
            files += [p for p in (root/folder).rglob('*') if p.is_file() and p.suffix in suffixes]
        violations=[]
        for p in files:
            for i,line in enumerate(p.read_text().splitlines(),1):
                # Underscores/letters remain word characters: env variables and
                # internal class names are not brand-copy violations.
                for match in re.finditer(r'\brepager\b',line,re.I):
                    if match.group()!='repager': violations.append(f'{p.relative_to(root)}:{i}: {match.group()}')
        self.assertEqual(violations,[], '\n'.join(violations))
