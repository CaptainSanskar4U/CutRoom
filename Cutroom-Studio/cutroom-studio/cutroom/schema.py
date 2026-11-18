from typing import Annotated, Literal
from pydantic import BaseModel, Field, StringConstraints, model_validator

Ratio = Literal['9:16','16:9','1:1','4:5']
Color = Annotated[str, StringConstraints(pattern=r'^#[0-9a-fA-F]{6}$')]
Id = Annotated[str, StringConstraints(pattern=r'^[a-f0-9]{32}$')]
Time = Annotated[float, Field(ge=0,le=86400,allow_inf_nan=False)]
Point = Annotated[float, Field(ge=0,le=1,allow_inf_nan=False)]
Font = Literal['DejaVu Sans','Liberation Sans','Liberation Serif','DejaVu Sans Mono','Noto Sans']

class Strict(BaseModel):
    model_config = {'extra':'forbid','str_strip_whitespace':True}

class Prefs(Strict):
    length: Literal['auto','short','medium','long'] = 'auto'
    ratio: Ratio = '9:16'
    layout: Literal['track','fit','split'] = 'track'
    language: Annotated[str, StringConstraints(pattern=r'^(auto|[a-z]{2,3})$')] = 'auto'
    subtitle_language: Annotated[str, StringConstraints(pattern=r'^(auto|[a-z]{2,3})$')] = 'auto'
    preset: Literal['pulse','hormozi','beast','cinema','studio','spotlight','mono'] = 'pulse'
    focus: str = Field('',max_length=500)
    count: int = Field(6,ge=1,le=10)
    brand: Id | None = None

class ProjectCreate(Strict):
    title: str = Field('',max_length=120)
    filename: str = Field('', max_length=200)
    bytes: int = Field(0,ge=0,le=20*1024**3)
    url: str | None = Field(None,max_length=2400)
    prefs: Prefs = Field(default_factory=Prefs)

class Title(Strict):
    title: str = Field(min_length=1,max_length=120)

class Auth(Strict):
    email: str = Field(min_length=3,max_length=240)
    password: str = Field(min_length=1,max_length=128)
    name: str = Field('',max_length=80)

class Settings(Strict):
    name: str = Field(min_length=1,max_length=80)
    ratio: Ratio = '9:16'
    language: Annotated[str, StringConstraints(pattern=r'^(auto|[a-z]{2,3})$')] = 'auto'

class Caption(Strict):
    enabled: bool = True
    preset: Literal['pulse','hormozi','beast','cinema','studio','spotlight','mono'] = 'pulse'
    font: Font = 'DejaVu Sans'
    font_id: Id | None = None
    size: int = Field(55,ge=20,le=110)
    color: Color = '#ffffff'
    highlight: Color = '#d9f770'
    background: Color | None = None
    outline: int = Field(3,ge=0,le=12)
    outline_color: Color = '#151020'
    shadow: int = Field(2,ge=0,le=12)
    position: Annotated[float,Field(ge=.08,le=.93,allow_inf_nan=False)] = .79
    uppercase: bool = True
    motion: Literal['word','pop','none'] = 'pop'
    offset: Annotated[float,Field(ge=-10,le=10,allow_inf_nan=False)] = 0
    words: int = Field(4,ge=1,le=8)

class Range(Strict):
    s: Time
    e: Time
    @model_validator(mode='after')
    def ordered(self):
        if self.e <= self.s: raise ValueError('End must be after start.')
        return self

class WordEdit(Strict):
    i: int = Field(ge=0,le=100000)
    t: str = Field(max_length=140)
    s: Time
    e: Time
    @model_validator(mode='after')
    def ordered(self):
        if self.e < self.s: raise ValueError('Caption end must not precede its start.')
        return self

class Overlay(Strict):
    type: Literal['text','image']
    text: str = Field('',max_length=160)
    asset: Id | None = None
    x: Point = .5
    y: Point = .18
    width: Annotated[float,Field(ge=.08,le=1,allow_inf_nan=False)] = .25
    color: Color = '#ffffff'
    size: int = Field(54,ge=20,le=110)
    start: Time | None = None
    end: Time | None = None
    @model_validator(mode='after')
    def valid(self):
        if self.type=='text' and not self.text: raise ValueError('Enter overlay text.')
        if self.type=='image' and not self.asset: raise ValueError('Choose an image.')
        if self.start is not None and self.end is not None and self.end<=self.start: raise ValueError('Invalid overlay timing.')
        return self

class Edit(Strict):
    ratio: Ratio = '9:16'
    framing: Literal['track','manual','fit','split'] = 'track'
    crop_x: Point = .5
    crop_y: Point = .5
    background: Color = '#171322'
    volume: Annotated[float,Field(ge=0,le=2,allow_inf_nan=False)] = 1
    fade: Annotated[float,Field(ge=0,le=2,allow_inf_nan=False)] = 0
    caption: Caption = Field(default_factory=Caption)
    word_edits: list[WordEdit] = Field(default_factory=list,max_length=3500)
    cuts: list[Range] = Field(default_factory=list,max_length=50)
    overlays: list[Overlay] = Field(default_factory=list,max_length=10)
    watermark: bool = False

class ClipUpdate(Strict):
    title: str = Field(min_length=1,max_length=120)
    start_at: Time
    end_at: Time
    edit: Edit
    version: int = Field(ge=1)

class Render(Strict):
    resolution: Literal[480,720,1080,2160] = 1080
    quality: Literal['compact','standard','high'] = 'standard'

class Brand(Strict):
    name: str = Field(min_length=1,max_length=60)
    caption: Caption = Field(default_factory=Caption)
    background: Color = '#171322'
    logo: Id | None = None

PRESETS = {
    'pulse':Caption().model_dump(),
    'hormozi':Caption(preset='hormozi', words=3, font='DejaVu Sans', size=58, uppercase=True, highlight='#ffe600', color='#ffffff', outline=4, outline_color='#0a0812', shadow=3, motion='pop').model_dump(),
    'beast':Caption(preset='beast', words=2, font='DejaVu Sans', size=62, uppercase=True, highlight='#ff3b30', color='#ffffff', outline=4, outline_color='#000000', shadow=4, motion='pop').model_dump(),
    'cinema':Caption(preset='cinema', words=5, font='Liberation Serif', size=42, uppercase=False, highlight='#e2e8f0', color='#f8fafc', outline=1, outline_color='#0f172a', shadow=1, motion='none', position=.84).model_dump(),
    'studio':Caption(preset='studio', words=6, font='Liberation Sans', size=45, uppercase=False, highlight='#e5d2ff', motion='word', outline=2).model_dump(),
    'spotlight':Caption(preset='spotlight', words=3, highlight='#ffcd6c', background='#1a1227', font='DejaVu Sans', size=51, motion='word', outline=1, shadow=0).model_dump(),
    'mono':Caption(preset='mono', words=5, font='DejaVu Sans Mono', size=40, motion='none', uppercase=False, outline=2, highlight='#ffffff').model_dump(),
}

def initial_edit(prefs_or_ratio, brand=None):
    if isinstance(prefs_or_ratio, dict):
        ratio = prefs_or_ratio.get('ratio', '9:16')
        framing = prefs_or_ratio.get('layout', 'track')
        preset_name = prefs_or_ratio.get('preset', 'pulse')
    else:
        ratio = prefs_or_ratio
        framing = 'track'
        preset_name = 'pulse'
    cap = PRESETS.get(preset_name, PRESETS['pulse'])
    data = Edit(ratio=ratio, framing=framing, caption=cap).model_dump()
    if brand:
        data.update(caption=brand['caption'], background=brand['background'])
        if brand.get('logo'): data['overlays'] = [Overlay(type='image', asset=brand['logo'], x=.85,y=.10,width=.18).model_dump()]
    return data
