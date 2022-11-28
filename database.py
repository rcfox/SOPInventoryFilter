from __future__ import annotations

import csv
import struct
import textwrap
from dataclasses import dataclass, asdict, field
from typing import (cast, ClassVar, Dict, Generator, Tuple, List, TypeVar,
                    Generic, Optional, Type)
from pathlib import Path
from pprint import pprint, pformat

from config import Config

INSTALL_DIR = Path(Config['General']['Install Directory'])

ITEM_TYPES: Dict[int, str] = {
    0: 'Currency',
    1: 'Consumable',
    3: 'Mission Item',
    27: 'Head',
    28: 'Body',
    29: 'Arm',
    30: 'Leg',
    31: 'Foot',
    32: 'Accessory',
    33: 'DLC2 Consumable',
    35: 'Memory',
    36: 'Crafting Ingredient',
    37: 'Staff',
    38: 'Sword',
    39: 'Greatsword',
    40: 'Katana',
    41: 'Mace',
    42: 'Axe',
    43: 'Knuckles',
    44: 'Dagger',
    45: 'Lance',
    47: 'Shield',
    48: 'Limit Release',
    49: 'Unlock',
    6948: 'Crest',
}

# Only used by body armor, indicates if another slot is used by the item.
# Everything else has 0.
SLOT_TYPES: Dict[int, str] = {0: 'Body', 2: 'Body-Leg', 16: 'Body-Head'}


@dataclass
class DBEntry:
    buffer: bytes
    id: int
    SIZE: ClassVar[int] = 0

    @classmethod
    def path(cls) -> Path:
        return INSTALL_DIR

    def values(self, format: str = '<I') -> List[Tuple[int, ...]]:
        size = struct.calcsize(format)
        padding = b'\x00' * (size - len(self.buffer) % size)
        return [(i * size, *x) for i, x in enumerate(
            struct.iter_unpack(format, self.buffer + padding))]

    def hex(self) -> str:
        return '\n'.join(
            textwrap.wrap(' '.join(textwrap.wrap(self.buffer.hex(), 2)), 48))

    @classmethod
    def from_bytes(cls, buffer: bytes, index: int) -> DBEntry:
        return cls(buffer, 0)

    @property
    def name(self) -> str:
        return ''
        
    @classmethod
    def create_table(cls, conn):
        pass
        
    def insert_row(self, conn):
        pass


@dataclass
class ItemDBEntry(DBEntry):
    string_id: int
    item_type: int
    slot_type: int
    SIZE: ClassVar[int] = 388

    @classmethod
    def path(cls) -> Path:
        return INSTALL_DIR / 'database/item_database.bin'

    @classmethod
    def from_bytes(cls, buffer: bytes, index: int) -> ItemDBEntry:
        item_id = struct.unpack_from('<I', buffer, 0)[0]
        item_type = struct.unpack_from('<H', buffer, 4)[0]
        string_id = struct.unpack_from('<I', buffer, 8)[0]
        slot_type = struct.unpack_from('<B', buffer, 336)[0]
        return cls(buffer, item_id, string_id, item_type, slot_type)
        
    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS items;
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            string_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            slot_type TEXT NOT NULL,
            FOREIGN KEY (string_id) REFERENCES strings (id)
        );
        ''')
        
    def insert_row(self, conn):
        conn.execute('''
        INSERT INTO items (
            id, string_id, item_type, slot_type
        ) VALUES (?, ?, ?, ?)
        ''', (self.id, self.string_id, self.type, self.slots))

    @property
    def name(self) -> str:
        return Strings.get(self.string_id)

    @property
    def type(self) -> str:
        return ITEM_TYPES.get(self.item_type, '(unknown)')

    @property
    def slots(self) -> str:
        if self.type == 'Body':
            if self.slot_type == 0:
                return '1-Slot Armour'
            else:
                return '2-Slot Armour'
        if self.type in ('Head', 'Arm', 'Leg', 'Foot'):
            return '1-Slot Armour'
        if self.type in ('Staff', 'Greatsword', 'Katana', 'Axe', 'Knuckles',
                         'Dagger', 'Lance'):
            return '2-Hand Weapon'
        if self.type in ('Sword', 'Mace'):
            return '1-Hand Weapon'
        if self.type in ('Shield', 'Accessory'):
            return self.type
        return ''


@dataclass
class EffectDBEntry(DBEntry):
    string_ids: Tuple[int, int, int, int]

    SIZE: ClassVar[int] = 96

    @classmethod
    def path(cls) -> Path:
        return INSTALL_DIR / 'database/special_bonus_database.bin'

    @classmethod
    def from_bytes(cls, buffer: bytes, index: int) -> EffectDBEntry:
        effect_id = struct.unpack_from('<I', buffer, 0)[0]
        string_ids = struct.unpack_from('<IIII', buffer, 40)
        return cls(buffer, effect_id,
                   cast(Tuple[int, int, int, int], string_ids))

    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS effects;
        CREATE TABLE effects (
            id INTEGER PRIMARY KEY,
            string_id INTEGER NOT NULL,
            FOREIGN KEY (string_id) REFERENCES strings (id)
        );
        ''')
        
    def insert_row(self, conn):
        conn.execute('''
        INSERT INTO effects (
            id, string_id
        ) VALUES (?, ?)
        ''', (self.id, self.string_ids[0]))

    def __repr__(self) -> str:
        return super().__repr__()

    @property
    def name(self) -> str:
        return Strings.get(self.string_ids[0])

    @property
    def string(self) -> str:
        return ''.join(
            Strings.get(s) for s in (self.string_ids[0], self.string_ids[3]))


@dataclass
class SkillDBEntry(DBEntry):
    name_id: int
    description_id: int
    source_id: int

    SIZE: ClassVar[int] = 104

    @classmethod
    def path(cls) -> Path:
        return INSTALL_DIR / 'database/P0030_ability_database.bin'

    @classmethod
    def from_bytes(cls, buffer: bytes, index: int) -> SkillDBEntry:
        skill_id = struct.unpack_from('<I', buffer, 0)[0]
        name_str_id = struct.unpack_from('<I', buffer, 16)[0]
        description_str_id = struct.unpack_from('<I', buffer, 20)[0]
        source_str_id = struct.unpack_from('<I', buffer, 24)[0]
        return cls(buffer, skill_id, name_str_id, description_str_id,
                   source_str_id)

    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS skills;
        CREATE TABLE skills (
            id INTEGER PRIMARY KEY,
            name_id INTEGER NOT NULL,
            description_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            FOREIGN KEY (name_id) REFERENCES strings (id),
            FOREIGN KEY (description_id) REFERENCES strings (id),
            FOREIGN KEY (source_id) REFERENCES strings (id)
        );
        ''')
        
    def insert_row(self, conn):
        conn.execute('''
        INSERT INTO skills (
            id, name_id, description_id, source_id
        ) VALUES (?, ?, ?, ?)
        ''', (self.id, self.name_id, self.description_id, self.source_id))
        
    def __repr__(self) -> str:
        return '\n'.join(
            textwrap.wrap(' '.join(textwrap.wrap(self.buffer.hex(), 2)), 48))

    @property
    def name(self) -> str:
        return Strings.get(self.name_id)

    @property
    def description(self) -> str:
        return Strings.get(self.description_id)

    @property
    def source(self) -> str:
        return Strings.get(self.source_id)


@dataclass
class JobDBEntry(DBEntry):
    string_id: int
    class_ids: Tuple[int, int]
    SIZE: ClassVar[int] = 100

    @classmethod
    def path(cls) -> Path:
        return INSTALL_DIR / 'database/P0031_job_database.bin'

    @classmethod
    def from_bytes(cls, buffer: bytes, index: int) -> JobDBEntry:
        affinity_id = struct.unpack_from('<B', buffer, 12)[0]
        string_id = struct.unpack_from('<I', buffer, 16)[0]
        class_ids = struct.unpack_from('<II', buffer, 20)
        return cls(buffer, affinity_id, string_id,
                   cast(Tuple[int, int], class_ids))

    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS jobs;
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY,
            name_id INTEGER NOT NULL,
            evocation_class_id INTEGER NOT NULL,
            ultima_class_id INTEGER NOT NULL,
            FOREIGN KEY (name_id) REFERENCES strings (id),
            FOREIGN KEY (evocation_class_id) REFERENCES strings (id),
            FOREIGN KEY (ultima_class_id) REFERENCES strings (id)
        );
        ''')
        
    def insert_row(self, conn):
        conn.execute('''
        INSERT INTO jobs (
            id, name_id, evocation_class_id, ultima_class_id
        ) VALUES (?, ?, ?, ?)
        ''', (self.id, self.string_id, self.class_ids[0], self.class_ids[1]))
        
    def __repr__(self) -> str:
        return self.hex()

    @property
    def name(self) -> str:
        return Strings.get(self.string_id)

    @property
    def classes(self) -> Tuple[str, str]:
        class1, class2 = self.class_ids
        return (Strings.get(class1), Strings.get(class2))


DBEntryType = TypeVar('DBEntryType', ItemDBEntry, EffectDBEntry, SkillDBEntry,
                      JobDBEntry)
#DBEntryType = TypeVar('DBEntryType', bound=DBEntry)


class Database(Generic[DBEntryType]):
    ALL_DBS = {}

    def __init__(self, entry_type: Type[DBEntryType]) -> None:
        Database.ALL_DBS[entry_type] = self
        
        self.entry_type: Type[DBEntryType] = entry_type
        self.entries: Dict[int, DBEntryType] = {}

    def __getitem__(self, key: int) -> DBEntryType:
        return self.entries[key]

    def get(self, key: int) -> Optional[DBEntryType]:
        return self.entries.get(key)

    def by_name(self, key: str) -> Generator[DBEntryType, None, None]:
        for entry in self.entries.values():
            if entry.name == key:
                yield entry

    def load(self) -> Database[DBEntryType]:
        self.entries.clear()
        with self.entry_type.path().open('rb') as f:
            buffer = f.read()

        index = 0
        head, count = struct.unpack_from('<II', buffer, 0)
        index += 8
        size = self.entry_type.SIZE
        for entry_index in range(count):
            entry = self.entry_type.from_bytes(buffer[index:index + size],
                                               entry_index)
            self.entries[entry.id] = entry
            index += size

        return self

    def to_csv(self, filename: str) -> None:
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            csv_w = csv.writer(f)
            for entry in self.entries.values():
                h = format(entry.id, '04X')
                h1, h2 = h[0:2], h[2:4]
                csv_w.writerow([h2 + h1, entry.name.replace('\r\n', '\\n')])
                
    @classmethod
    def populate(cls, conn):
        for db in cls.ALL_DBS.values():
            db.entry_type.create_table(conn)
            for entry in db.entries.values():
                entry.insert_row(conn)


@dataclass
class Strings:
    filename: str
    strings: Dict[int, str]
    base_path: ClassVar[Path] = INSTALL_DIR / 'string'
    files: ClassVar[Dict[str, 'Strings']] = {}
    
    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS strings;
        CREATE TABLE strings (
            id INTEGER PRIMARY KEY,
            string TEXT NOT NULL,
            filename TEXT NOT NULL
        );
        ''')
        
        for filename, file in Strings.files.items():
            conn.executemany('''
                INSERT INTO strings (
                    id, string, filename
                ) VALUES (?, ?, ?)
            ''', ((id, string, filename) for id, string in file.strings.items()))

    @classmethod
    def load_language(cls, language: str) -> None:
        for path in Strings.language_files(language):
            file = Strings.load_file(path)
            cls.files[file.filename] = file

    @classmethod
    def language_files(cls, language: str) -> Generator[Path, None, None]:
        return cls.base_path.glob(f'*_{language}.bin')

    @classmethod
    def load_file(cls, filename: Path) -> Strings:
        with filename.open('rb') as f:
            data = f.read()
        offset = 0
        strings = {}
        while offset < len(data):
            string_id = struct.unpack_from('<I', data, offset)[0]
            length = struct.unpack_from('<I', data, offset + 4)[0]
            string = struct.unpack_from(f'<{length*2}s', data,
                                        offset + 8)[0].decode('utf-16')[:-1]
            strings[string_id] = string
            offset += length * 2 + 8
        return cls('_'.join(filename.stem.split('_')[:-1]), strings)

    @classmethod
    def get(cls, string_id: int) -> str:
        if string_id in (0, 0xffffffff):
            return ''
        for filename in Strings.files.keys():
            strings = Strings.files[filename].strings
            if string_id in strings:
                return strings[string_id]
        raise Exception(f'String ID {string_id} not found.')


Strings.load_language('eng')
ItemsDB = Database(ItemDBEntry).load()
EffectsDB = Database(EffectDBEntry).load()
SkillsDB = Database(SkillDBEntry).load()
JobsDB = Database(JobDBEntry).load()
