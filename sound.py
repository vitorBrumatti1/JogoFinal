"""Carrega os sons uma vez; falha de dispositivo não impede a partida."""

from pathlib import Path
import arcade


class Audio:
    def __init__(self):
        self.muted = False
        self.sounds = {}
        self.players = []
        for name in (
            "jump",
            "clear",
            "shot_ak",
            "shot_smg",
            "shot_shotgun",
            "shot_rifle",
            "impact",
            "damage",
            "dash",
            "land",
            "menu",
            "victory",
            "defeat",
            "reload_v4",
            "boom_v4",
            "coin_v4",
        ):
            try:
                self.sounds[name] = arcade.load_sound(
                    str(Path(__file__).parent / "assets" / f"{name}.wav")
                )
            except Exception:
                pass

    def play(self, name):
        if self.muted or name not in self.sounds:
            return
        self.players = [p for p in self.players if p.playing]
        if len(self.players) >= 16:
            return
        try:
            player = arcade.play_sound(
                self.sounds[name],
                volume=(
                    0.28
                    if name.startswith("shot")
                    else (0.18 if name == "land" else 0.4)
                ),
            )
            if player:
                self.players.append(player)
        except Exception:
            pass

    def toggle(self):
        self.muted = not self.muted
        if self.muted:
            for p in self.players:
                p.pause()
            self.players.clear()
