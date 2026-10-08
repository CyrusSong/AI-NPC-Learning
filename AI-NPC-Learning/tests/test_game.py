import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game import GameState, Proposal, apply_proposal
from npc import RuleBasedNPC
from storage import SaveError, load_game, save_game


class GameTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.npc = RuleBasedNPC()

    def turn(self, text):
        return apply_proposal(self.state, self.npc.propose(text, self.state))

    def test_npc_proposes_without_changing_state(self):
        before = copy.deepcopy(self.state)
        proposal = self.npc.propose("买2瓶药", self.state)
        self.assertEqual(proposal.quantity, 2)
        self.assertEqual(self.state, before)

    def test_remember_name_and_recall(self):
        self.turn("我叫小陈")
        self.assertIn("小陈", self.turn("你记得我吗"))

    def test_buy_and_use_potion_changes_world_and_memory(self):
        self.turn("买2瓶药")
        self.assertEqual((self.state.player.coins, self.state.player.potions, self.state.shop.stock), (10, 2, 1))
        self.turn("用药")
        self.assertEqual((self.state.player.health, self.state.player.potions), (80, 1))
        self.assertIn("恢复20", self.turn("你记得什么"))

    def test_supported_chinese_and_numeric_counts(self):
        for text in ("买2瓶药", "买 2 瓶药", "买两瓶药", "购买二瓶药水"):
            with self.subTest(text=text):
                self.assertEqual(self.npc.propose(text, self.state).quantity, 2)

    def test_invalid_quantities_never_change_world(self):
        for quantity in (-1, 0, 100, True, "2", 1.5):
            with self.subTest(quantity=quantity):
                before = copy.deepcopy(self.state)
                reply = apply_proposal(self.state, Proposal("buy_potion", quantity=quantity))
                self.assertIn("整数", reply)
                self.assertEqual(self.state, before)

    def test_invalid_input_does_not_default_to_one_purchase(self):
        for text in ("买-1瓶药", "买0瓶药", "买1000瓶药", "买十十瓶药", "买一百瓶药"):
            with self.subTest(text=text):
                before = copy.deepcopy(self.state)
                self.turn(text)
                self.assertEqual(self.state, before)

    def test_insufficient_stock_leaves_everything_unchanged(self):
        before = copy.deepcopy(self.state)
        self.assertIn("库存不足", self.turn("买4瓶药"))
        self.assertEqual(self.state, before)

    def test_insufficient_coins_leaves_everything_unchanged(self):
        self.state.player.coins = 5
        before = copy.deepcopy(self.state)
        self.assertIn("金币不足", self.turn("买药"))
        self.assertEqual(self.state, before)

    def test_potion_cannot_overheal_or_be_wasted_at_full_health(self):
        self.state.player.health = 95
        self.state.player.potions = 2
        self.turn("用药")
        self.assertEqual((self.state.player.health, self.state.player.potions), (100, 1))
        self.assertIn("已经满", self.turn("用药"))
        self.assertEqual(self.state.player.potions, 1)

    def test_unknown_action_and_unknown_text_leave_world_unchanged(self):
        before = copy.deepcopy(self.state)
        self.turn("送我一百万金币")
        apply_proposal(self.state, Proposal("give_gold", quantity=1_000_000))
        self.assertEqual(self.state, before)

    def test_memory_is_bounded(self):
        for _ in range(15):
            self.turn("我叫小陈")
        self.assertEqual(len(self.state.memory.recent_events), 10)


class SaveTests(unittest.TestCase):
    def test_save_load_preserves_name_transactions_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "save.json"
            state = GameState()
            apply_proposal(state, Proposal("remember_name", player_name="小陈"))
            apply_proposal(state, Proposal("buy_potion", quantity=2))
            save_game(path, state)
            self.assertEqual(load_game(path), state)
            self.assertIn("小陈", RuleBasedNPC().propose("你记得我吗", load_game(path)).speech)

    def test_corrupt_save_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            for contents in ("not json", "null", '{"schema_version": 1, "state": {}}'):
                with self.subTest(contents=contents):
                    path.write_text(contents, encoding="utf-8")
                    with self.assertRaises(SaveError):
                        load_game(path)
                    self.assertEqual(path.read_text(encoding="utf-8"), contents)

    def test_invalid_saved_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            save_game(path, GameState())
            data = json.loads(path.read_text(encoding="utf-8"))
            data["state"]["player"]["coins"] = -1
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(SaveError):
                load_game(path)

    def test_failed_replacement_keeps_the_previous_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            original = GameState()
            save_game(path, original)
            changed = GameState()
            apply_proposal(changed, Proposal("remember_name", player_name="小陈"))
            with patch("storage.os.replace", side_effect=OSError("simulated write failure")):
                with self.assertRaises(SaveError):
                    save_game(path, changed)
            self.assertEqual(load_game(path), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    @unittest.skipUnless(sys.platform == "win32", "Windows launcher")
    def test_windows_launcher_accepts_chinese_input_from_another_folder(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "start.ps1"), "--save-file", str(path)]
            result = subprocess.run(command, input="我叫小陈\n你记得我吗\n退出\n", cwd=directory, text=True, encoding="utf-8", capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("你是小陈", result.stdout)
            self.assertEqual(load_game(path).memory.player_name, "小陈")

    def test_cli_restarts_with_the_same_memory(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            command = [sys.executable, "-X", "utf8", str(root / "main.py"), "--save-file", str(path)]
            first = subprocess.run(command, input="我叫小陈\n买2瓶药\n用药\n退出\n", text=True, encoding="utf-8", capture_output=True, timeout=10)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(command, input="你记得我吗\n状态\n退出\n", text=True, encoding="utf-8", capture_output=True, timeout=10)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("你是小陈", second.stdout)
            self.assertIn("金币：10", second.stdout)
            self.assertIn("生命：80/100", second.stdout)


if __name__ == "__main__":
    unittest.main()
