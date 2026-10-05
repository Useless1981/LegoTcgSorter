from abc import ABC, abstractmethod


class Card(ABC):
    """
    Abstract interface representing a generic Trading Card.
    Defines the contract that all specific TCG implementations must follow.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns the legal name of the card."""
        pass

    @abstractmethod
    def get_id(self) -> str:
        """Returns a unique identifier (e.g., collector number or internal database ID)."""
        pass

    @abstractmethod
    def get_target_bin(self) -> int:
        """
        Evaluates the card's attributes and determines the sorting destination.
        :return: Integer index of the target sorting bin
        """
        pass


class MtgCard(Card):
    """
    Concrete implementation of a Magic: The Gathering card.
    """

    def __init__(self, name: str, collector_num: str, color: str, rarity: str, cost: str, text: str, card_type: str, effect: str = 'nofx'):
        self.name = name
        self.collector_num = collector_num
        self.color = color.upper()  # e.g., 'W', 'U', 'B', 'R', 'G', 'COLORLESS'
        self.rarity = rarity.lower()  # e.g., 'common', 'uncommon', 'rare', 'mythic'
        self.cost = cost.upper()
        self.text = text
        self.card_type = card_type.lower()
        self.effect = effect.lower()
        self.target_bin: int = 0


    def get_name(self) -> str:
        return self.name

    def get_id(self) -> str:
        return self.collector_num

    def get_color(self) -> str:
        return self.color

    def get_card_type(self) -> str:
        return self.card_type

    def get_rarity(self) -> str:
        return self.rarity

    def get_text(self) -> str:
        return self.text

    def get_cost(self) -> str:
        return self.cost

    def get_effect(self) -> str:
        return self.effect

    def get_target_bin(self) -> int:
        return self.target_bin

    def set_target_bin(self, target_bin: int):
        self.target_bin = target_bin


class PokemonCard(Card):
    """
    Concrete implementation of a Pokémon Trading Card.
    """

    def __init__(self, name: str, id_string: str, card_type: str, rarity: str):
        self.name = name
        self.id_string = id_string  # e.g., 'G1-042' or database index
        self.card_type = card_type.upper()  # e.g., 'FIRE', 'WATER', 'GRASS', 'TRAINER'
        self.rarity = rarity.lower()  # e.g., 'common', 'holo rare', 'ultra rare'
        self.target_bin: int = 0

    def get_name(self) -> str:
        return self.name

    def get_id(self) -> str:
        return self.id_string

    def get_card_type(self) -> str:
        return self.card_type

    def get_rarity(self) -> str:
        return self.rarity

    def get_target_bin(self) -> int:
        return self.target_bin

    def set_target_bin(self, target_bin: int):
        self.target_bin = target_bin
