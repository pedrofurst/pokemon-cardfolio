from pydantic import BaseModel


class CardPayload(BaseModel):
    id: str
    name: str = ""
    set_name: str = ""
    set_id: str = ""
    set_total: int | None = None
    number: str = ""
    rarity: str = ""
    image_url: str = ""
    tcgplayer_id: str | None = None
    market_price: float | None = None
