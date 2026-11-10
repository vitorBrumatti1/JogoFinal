"""Modelo relacional; nenhuma responsabilidade de interface gráfica."""

import datetime
from pathlib import Path
from peewee import (
    Model,
    SqliteDatabase,
    CharField,
    IntegerField,
    FloatField,
    DateTimeField,
)

banco = SqliteDatabase(str(Path(__file__).resolve().parent / "ranking.db"))


class BaseModel(Model):
    class Meta:
        database = banco


class Pontuacao(BaseModel):
    nome_jogador = CharField()
    pontos = IntegerField()
    tempo_partida = FloatField()
    data_hora = DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return f"{self.nome_jogador} - {self.pontos} pts ({self.tempo_partida:.1f}s)"


def inicializar_banco():
    banco.connect(reuse_if_open=True)
    banco.create_tables([Pontuacao], safe=True)
