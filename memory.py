from __future__ import annotations

import struct
import textwrap
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import cast, ClassVar, Dict, Tuple, List, Optional
from pprint import pprint, pformat

from config import Config
from database import ItemsDB, EffectsDB, JobsDB

import pymem

class InvalidItemException(Exception):
    pass


@dataclass
class Effect:
    effect_id: int
    raw_amount: int
    unknown1: bytes
    affinity_level: int
    affinity_type: int
    unknown2: bytes
    FIRST: ClassVar[int] = 0x28
    SIZE: ClassVar[int] = 24
    COUNT: ClassVar[int] = 8

    @classmethod
    def from_bytes(cls, data: bytes) -> Effect:
        id = struct.unpack_from('<I', data, 0x00)[0]
        raw_amount = struct.unpack_from('<I', data, 0x04)[0]
        unknown1 = data[0x08 : 0x0C]
        affinity_level = struct.unpack_from('<B', data, 0x0C)[0]
        affinity_type = struct.unpack_from('<B', data, 0x0D)[0]
        unknown2 = data[0x0E : 0x18]
        return cls(id, raw_amount, unknown1, affinity_level, affinity_type,
                   unknown2)
    
    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS effect_instances;
        CREATE TABLE effect_instances (
            id INTEGER PRIMARY KEY,
            effect_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            affinity_level INTEGER NOT NULL,
            affinity_type INTEGER NOT NULL,
            unknown1 BLOB NOT NULL,
            unknown2 BLOB NOT NULL,
            FOREIGN KEY (effect_id) REFERENCES effects (id),
            FOREIGN KEY (owner_id) REFERENCES item_instances (id)
        );
        ''')

    def insert_row(self, conn, owner_id: int):
        conn.execute('''
        INSERT INTO effect_instances(
            effect_id, owner_id, amount, 
            affinity_level, affinity_type,
            unknown1, unknown2
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.effect_id, owner_id, self.raw_amount,
            self.affinity_level, self.affinity_type,
            self.unknown1, self.unknown2
        ))

    @property
    def amount(self) -> str:
        return f'{self.raw_amount}'

    def db_hex(self) -> str:
        return EffectsDB[self.effect_id].__repr__()

    @property
    def name(self) -> str:
        if self.effect_id == 0:
            return '(none)'
        return EffectsDB[self.effect_id].string

    @property
    def color(self) -> str:
        if self.affinity_type == 1:
            return 'Evocation'
        if self.affinity_type == 2:
            return 'Ultima'
        return 'Chaos'

    def __repr__(self) -> str:
        affinity = ''
        if self.affinity_level > 0:
            affinity = f'({self.color}: {self.affinity_level - 1}) '
        return f'{affinity}{self.name}: {self.amount}'  #-- {hex(self.unknown1)} -- {[hex(x) for x in self.unknown2]}'


@dataclass
class Item:
    _process: Optional[pymem.Pymem]
    _address: int
    _buffer: bytes

    item_id: int
    amount: int
    level: int
    original_level: int
    rarity: int
    status: int
    slot_pos: Tuple[int, int]
    effects: List[Effect]

    attack: int
    defense: int
    magic: int
    resist: int

    job1: Tuple[int, int, int]
    job2: Tuple[int, int, int]
    skills: Tuple[int, int, int, int]

    summon: Tuple[int, int]

    ITEMS_START: ClassVar[int] = 0 # This is gross, but it will be set by Inventory.find_offset() now.
    STRUCT_SIZE: ClassVar[int] = 0x148

    @classmethod
    def from_process(cls, process: pymem.Pymem, index: int) -> Item:
        address = (process.base_address + Item.ITEMS_START +
                   index * Item.STRUCT_SIZE)
        data = process.read_bytes(address, Item.STRUCT_SIZE)
        return cls.from_bytes(data, address=address, process=process)

    @classmethod
    def from_bytes(cls,
                   data: bytes,
                   address: int = 0,
                   process: Optional[pymem.Pymem] = None) -> Item:
        id = struct.unpack_from('<II', data, 0x00)
        if id[0] != id[1]:
            raise InvalidItemException('Item IDs do not match')

        amount = struct.unpack_from('<H', data, 0x08)[0]

        level = struct.unpack_from('<H', data, 0x0A)[0]
        original_level = struct.unpack_from('<H', data, 0x013A)[0]

        rarity = struct.unpack_from('<B', data, 0x0C)[0]

        status = struct.unpack_from('<I', data, 0x10)[0]

        slot_pos = cast(Tuple[int, int], struct.unpack_from('<II', data, 0x14))

        effects = []
        for i in range(Effect.COUNT):
            start = Effect.FIRST + i * Effect.SIZE
            end = Effect.FIRST + (i + 1) * Effect.SIZE
            effect = Effect.from_bytes(data[start:end])
            if effect.effect_id != 0:
                effects.append(effect)

        attack = struct.unpack_from('<I', data, 0xE8)[0]
        defense = struct.unpack_from('<I', data, 0xEC)[0]
        magic = struct.unpack_from('<I', data, 0xF0)[0]
        resist = struct.unpack_from('<I', data, 0xF4)[0]

        job1 = cast(Tuple[int, int, int],
                    struct.unpack_from('<IIB', data, 0x0110))
        job2 = cast(Tuple[int, int, int],
                    struct.unpack_from('<IIB', data, 0x011C))

        skills = cast(Tuple[int, int, int, int],
                      struct.unpack_from('<IIII', data, 0x0128))

        summon = cast(Tuple[int, int], struct.unpack_from('<II', data, 0x013C))

        return Item(process, address, data, id[0], amount, level,
                    original_level, rarity, status, slot_pos, effects, attack,
                    defense, magic, resist, job1, job2, skills, summon)
                    

    @classmethod
    def create_table(cls, conn):
        conn.executescript('''
        DROP TABLE IF EXISTS item_instances;
        CREATE TABLE item_instances (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            level INTEGER NOT NULL,
            original_level INTEGER NOT NULL,
            rarity INTEGER NOT NULL,
            status INTEGER NOT NULL,
            slot_pos1 INTEGER NOT NULL,
            slot_pos2 INTEGER NOT NULL,
            summon_id INTEGER NOT NULL,
            summon_level INTEGER NOT NULL,
            FOREIGN KEY (item_id) REFERENCES items (id)
        );
        
        DROP TABLE IF EXISTS item_skills;
        CREATE TABLE item_skills (
            id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            skill INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES item_instances (id)
        );
        
        DROP TABLE IF EXISTS item_jobs;
        CREATE TABLE item_jobs (
            id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            job_level INTEGER NOT NULL,
            job_type INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES item_instances (id),
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        );
        ''')

    def insert_row(self, conn):
        conn.execute('''
        INSERT INTO item_instances(
            item_id, amount, level, original_level, rarity, status,
            slot_pos1, slot_pos2, summon_id, summon_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.item_id, self.amount, self.level, self.original_level, 
            self.rarity, self.status, self.slot_pos[0], self.slot_pos[1],
            self.summon[0], self.summon[1]
        ))
        
        owner_id, *_ = conn.execute('SELECT last_insert_rowid()').fetchone()
        
        for effect in self.effects:
            effect.insert_row(conn, owner_id)
            
        conn.executemany('''
            INSERT INTO item_skills (owner_id, skill) VALUES (?, ?)
        ''', [(owner_id, skill) for skill in self.skills if skill != 0])
        
        conn.executemany('''
            INSERT INTO item_jobs (owner_id, job_id, job_level, job_type) VALUES (?, ?, ?, ?)
        ''', [(owner_id, *job) for job in [self.job1, self.job2] if job[0] != 0])

    @property
    def name(self) -> str:
        if self.item_id == 0:
            return '(none)'
        return ItemsDB[self.item_id].name

    @property
    def type(self) -> str:
        if self.item_id == 0:
            return '(none)'
        return ItemsDB[self.item_id].type

    def __repr__(self) -> str:
        values = dict(self.__dict__)
        values.pop('_address')
        values.pop('_process')
        return pformat(values)
        
    def set_status(self, status):
        if self._process:
            self._process.write_uchar(self._address + 0x10, status)

    @property
    def locked(self) -> bool:
        return bool(self.status & 0x02)

    @locked.setter
    def locked(self, locked: bool) -> None:
        self.status = (self.status & ~0x02) | 0x02 * locked
        self.set_status(self.status)

    @property        
    def is_new(self) -> bool:
        return bool(self.status & 0x01)
        
    @is_new.setter
    def is_new(self, new: bool) -> None:
        self.status = (self.status & ~0x01) | 0x01 * new
        self.set_status(self.status)

    def hex(self) -> str:
        return '\n'.join(
            textwrap.wrap(' '.join(textwrap.wrap(self._buffer.hex(), 2)), 48))

    def should_keep(self) -> bool:
        db_entry = ItemsDB.get(self.item_id)
        if not db_entry or not db_entry.slots:
            return False

        filters = Config['Effects']

        for effect in self.effects:
            if filters.getint(effect.name,
                              fallback=-1) < effect.affinity_level:
                return True

        slot_type = db_entry.slots
        if slot_type != 'Accessory':
            try:
                if Config['Keep Artifacts'].getboolean(slot_type,
                                                       fallback=False):
                    if self.job1[0] != 0 and self.job2[0] != 0:
                        return True

            except ValueError:
                if Config['Keep Artifacts'].get(slot_type,
                                                fallback='') == 'blessed':
                    if self.summon[0] != 0:
                        return True

            min_affinity = Config['Minimum Affinity'].getint(slot_type,
                                                             fallback=9999)
            if self.job1[1] >= min_affinity:
                return True

        return False


@dataclass
class Inventory:
    items: List[Item]

    def save(self, filename: Path) -> None:
        with filename.open('wb') as f:
            f.write(struct.pack('<II', 0, len(self.items)))
            for item in self.items:
                f.write(item._buffer)

    def filter(self) -> List[Item]:
        results = []
        weapon_skills: Dict[int, bool] = defaultdict(bool)
        acc_skills: Dict[int, bool] = defaultdict(bool)

        not_kept = []

        for item in self.items:
            db_item = ItemsDB.get(item.item_id)
            if db_item is None:
                continue

            keep = item.should_keep()
            if keep:
                results.append(item)
            else:
                not_kept.append(item)

            for skill in item.skills:
                if skill != 0:
                    item_type = db_item.slots
                    if 'Weapon' in item_type:
                        weapon_skills[skill] |= keep
                    elif 'Accessory' in item_type:
                        acc_skills[skill] |= keep
                    else:
                        raise Exception(
                            f'unexpected skill {skill} on {item.name}')

        for item in not_kept:
            for skill in item.skills:
                if skill != 0:
                    if Config['Skills'].getboolean(
                            'Keep One Of Each Weapon Skill'):
                        if weapon_skills.get(skill) is False:
                            results.append(item)
                            weapon_skills[skill] = True
                    if Config['Skills'].getboolean(
                            'Keep One Of Each Accessory Skill'):
                        if acc_skills.get(skill) is False:
                            results.append(item)
                            acc_skills[skill] = True

        return results
        
    @classmethod
    def find_offset(cls) -> int:
        pm = pymem.Pymem('SOPFFO.exe')
        
        def scan_back(address: int) -> int:
            try:
                while True:
                    i = Item.from_bytes(pm.read_bytes(address, Item.STRUCT_SIZE))
                    address -= Item.STRUCT_SIZE
            except InvalidItemException:
                return address + Item.STRUCT_SIZE
        
        # Look for the potion item ID. Everyone should have this.
        possible_potions = pm.pattern_scan_module(b'\xe7\x05\x00\x00\xe7\x05\x00\x00', 'SOPFFO.exe', return_multiple=True)
        for addr in possible_potions:
            Item.ITEMS_START = scan_back(addr) - pm.base_address
            try:
                _ = Inventory.from_process(pm)
                return Item.ITEMS_START
            except InvalidItemException:
                continue
                
        raise Exception('Could not find inventory offset!')

    @classmethod
    def from_process(cls, pm: Optional[pymem.Pymem] = None) -> Inventory:
        if pm is None:
            pm = pymem.Pymem('SOPFFO.exe')
            
        if Item.ITEMS_START == 0:
            Item.ITEMS_START = Inventory.find_offset()
            
        items = []
        try:
            for i in range(5500):
                items.append(Item.from_process(pm, i))
        except InvalidItemException:
            if i > 5:
                print('---', i)
            raise
        return cls(items)

    @classmethod
    def from_file(cls, filename: Path) -> Inventory:
        items = []
        with filename.open('rb') as f:
            buffer = f.read()
            index = 0
            _, size = struct.unpack('<II', buffer[0:8])
            index += 8
            for _ in range(size):
                item = Item.from_bytes(buffer[index:index + Item.STRUCT_SIZE],
                                       address=index)
                items.append(item)
                index += Item.STRUCT_SIZE
        return cls(items)
