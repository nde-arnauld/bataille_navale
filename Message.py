import json

class Message:
    def __init__(self, type_: str, donnees: dict):
        self.type = type_
        self.donnees = donnees

    def vers_json(self) -> str:
        return json.dumps({"type": self.type, "donnees": self.donnees})

    @staticmethod
    def depuis_json(chaine: str):
        data = json.loads(chaine)
        return Message(data["type"], data["donnees"])

