"""Policy probes never dispatch inference or read the live host config."""
import copy
import sys
import unittest
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
from repager.runtime import check_model_policy, HostLlm
from repager.service import ServiceError

BASE = {'model': {'provider': 'openai-codex', 'default': 'gpt-6.1-sol'},
        'fallback_providers': [], 'fallback_model': {},
        'auxiliary': {'repager_layout': {'provider': 'openai-codex', 'model': 'gpt-6.1-sol', 'fallback_chain': []}}}

class RoutingTests(unittest.TestCase):
    def call(self, config, backend):
        module = ModuleType('hermes_cli.config')
        module.load_config_readonly = lambda: config
        context = SimpleNamespace(get_config=lambda *args: True, llm=SimpleNamespace(complete_structured=backend))
        with patch.dict(sys.modules, {'hermes_cli.config': module}):
            return HostLlm(context).complete_structured()

    def test_known_explicit_route_and_empty_fallbacks(self):
        self.assertEqual(check_model_policy(BASE), {'provider': 'openai-codex', 'model': 'gpt-6.1-sol'})

    def test_free_router_aliases_rejected(self):
        for alias in ('openrouter/free', 'x:free', 'free', 'free/model', 'router-free'):
            with self.subTest(alias=alias):
                cfg = copy.deepcopy(BASE)
                cfg['auxiliary']['repager_layout']['model'] = alias
                with self.assertRaises(ServiceError): check_model_policy(cfg)

    def test_no_aux_provider_model_inheritance_or_ambiguous_fallback(self):
        for mutate in (lambda c: c.pop('auxiliary'),
                       lambda c: c['auxiliary']['repager_layout'].pop('model'),
                       lambda c: c['auxiliary']['repager_layout'].pop('provider'),
                       lambda c: c['auxiliary']['repager_layout'].pop('fallback_chain'),
                       lambda c: c.update(fallback_providers=[{'provider': 'auto'}]),
                       lambda c: c.update(fallback_model={'provider': 'openai-codex', 'model': 'paid'}),
                       lambda c: c['auxiliary']['repager_layout'].update(provider='auto')):
            cfg = copy.deepcopy(BASE); mutate(cfg)
            with self.assertRaises(ServiceError): check_model_policy(cfg)

    def test_malformed_fallback_types_are_not_treated_as_empty(self):
        for field, values in (('fallback_providers', (None, False, 0, '', {})),
                              ('fallback_model', (False, 0, '', []))):
            for value in values:
                cfg = copy.deepcopy(BASE); cfg[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ServiceError): check_model_policy(cfg)

    def test_preflight_refusal_never_dispatches(self):
        calls = []; cfg = copy.deepcopy(BASE)
        cfg['auxiliary']['repager_layout']['model'] = 'openrouter/free'
        with self.assertRaises(ServiceError): self.call(cfg, lambda **kw: calls.append(kw))
        self.assertEqual(calls, [])

    def test_attribution_mismatch_is_discarded_not_claimed_prevented(self):
        with self.assertRaisesRegex(ServiceError, 'cannot undo inference'):
            self.call(BASE, lambda **kw: SimpleNamespace(provider='other', model='other'))
