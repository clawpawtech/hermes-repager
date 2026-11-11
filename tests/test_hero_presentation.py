"""Regression tests for readable, bounded hero rendering."""
import unittest
from test_core_renderer import FULL_SPEC, _source
from repager.renderer import render_section

class HeroPresentation(unittest.TestCase):
    def test_hero_has_bounded_responsive_type_and_readable_measure(self):
        html = render_section(FULL_SPEC, _source())
        self.assertIn('font-size:clamp(34px,4.5vw,64px)', html)
        self.assertIn('max-width:65ch', html)
        self.assertIn('max-width:22ch', html)
        self.assertIn('<main>', html)
        self.assertIn('<section class="rp-section', html)
        self.assertIn('>Headline</h1>', html)
        self.assertIn('Body copy &lt;b&gt;keep&lt;/b&gt;', html)
        self.assertNotIn('—', html)

    def test_center_alignment_centers_copy_measure_in_both_layouts(self):
        for layout in ('stack','split'):
            html = render_section(dict(FULL_SPEC, layout=layout, alignment='center'), _source())
            self.assertIn('margin-inline:auto', html)
            self.assertIn('text-align:center', html)

if __name__ == '__main__':
    unittest.main()
