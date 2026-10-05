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

    def __init__(self, name: str, collector_num: str, color: str, rarity: str):
        self.name = name
        self.collector_num = collector_num
        self.color = color.upper()  # e.g., 'W', 'U', 'B', 'R', 'G', 'COLORLESS'
        self.rarity = rarity.lower()  # e.g., 'common', 'uncommon', 'rare', 'mythic'

    def get_name(self) -> str:
        return self.name

    def get_id(self) -> str:
        return self.collector_num

    def get_target_bin(self) -> int:
        """
        Example sorting logic for MtG: Sort by color.
        Maps the 5 basic Magic colors to specific LEGO sorting bins.
        """
        color_mapping = {
            'W': 1,  # White
            'U': 2,  # Blue
            'B': 3,  # Black
            'R': 4,  # Red
            'G': 5,  # Green
        }
        # Default to bin 0 for colorless, artifacts, or multicolor cards
        return color_mapping.get(self.color, 0)


class PokemonCard(Card):
    """
    Concrete implementation of a Pokémon Trading Card.
    """

    def __init__(self, name: str, id_string: str, card_type: str, rarity: str):
        self.name = name
        self.id_string = id_string  # e.g., 'G1-042' or database index
        self.card_type = card_type.upper()  # e.g., 'FIRE', 'WATER', 'GRASS', 'TRAINER'
        self.rarity = rarity.lower()  # e.g., 'common', 'holo rare', 'ultra rare'

    def get_name(self) -> str:
        return self.name

    def get_id(self) -> str:
        return self.id_string

    def get_target_bin(self) -> int:
        """
        Example sorting logic for Pokémon: Sort by card type (Energy/Element).
        """
        type_mapping = {
            'GRASS': 1,
            'FIRE': 2,
            'WATER': 3,
            'LIGHTNING': 4,
            'PSYCHIC': 5,
            'TRAINER': 6,
        }
        # Default to bin 0 for Special types, Colorless, or unrecognized energies
        return type_mapping.get(self.card_type, 0)
