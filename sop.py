from typing import Optional
from memory import Inventory, Item, Effect
from collections import defaultdict
from database import Database, Strings, ItemsDB
from pathlib import Path
import csv
import sqlite3
import click


def diff(a: str, b: str) -> str:
    result = []
    for ac, bc in zip(a, b):
        if ac == bc:
            result.append(ac)
        else:
            result.append('\033[31m' + bc + '\033[39m')
    return ''.join(result)

def listing() -> None:
    effects = defaultdict(lambda: defaultdict(int))
    inv = Inventory.from_process()
    for item in inv.items:
        if item.item_id == 0 or 'Accessory' in ItemsDB[item.item_id].slots:
            continue
        for eff in item.effects:
            effects[eff.name][eff.affinity_level] += 1
          
    with open('counts.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for effect, levels in sorted(effects.items()):
            row = [effect] + [levels.get(level, 0) for level in range(10)]
            writer.writerow(row)
            
def create_db(inventory):
    conn = sqlite3.connect('sop.db')
    try:
        with conn:
            Item.create_table(conn)
            Effect.create_table(conn)
            Strings.create_table(conn)
            Database.populate(conn)
            
            for item in inventory.items:
                item.insert_row(conn)
    finally:
        conn.close()
        
@click.group()
def main():
    pass
        
@main.command()
def unlock_all() -> None:
    print('Unlocking all items.')
    inv = Inventory.from_process()
    for item in inv.items:
        item.locked = False
        
@main.command()
@click.argument('marker', required=False, default=None)
def clear_markers(marker: Optional[int]) -> None:
    inv = Inventory.from_process()
    if marker is None:
        print('Clearing all markers.')    
        for item in inv.items:        
            item.clear_markers()
    else:
        print(f'Clearing all marker #{marker}.')
        for item in inv.items:
            item.unset_marker(int(marker))
        
@main.command()
def upgrades() -> None:   
    inv = Inventory.from_process()#Inventory.from_file(Path('inv.bin'))
    statuses = defaultdict(list)
    
    item_types = defaultdict(list)
    upgrade = []

    for item in inv.items:
        if item.item_id == 0:
            continue
        item_types[item.type].append(item)
        if ItemsDB[item.item_id].slots == '2-Slot Armour':
            item_types['Head'].append(item)
            item_types['Leg'].append(item)
        if Item.INPUT_MARKER in item.get_markers():
            upgrade.append(item)
            
    possible_upgrades = []
    for upgrade_item in upgrade:
        for item in item_types[upgrade_item.type]:
            if Item.INPUT_MARKER in item.get_markers():
                continue
            for upgrade_eff in upgrade_item.effects:
                for item_eff in item.effects:
                    if upgrade_eff.effect_id == item_eff.effect_id:
                        if upgrade_item.type == 'Accessory':
                            if item_eff.raw_amount > upgrade_eff.raw_amount:
                                possible_upgrades.append((upgrade_item, upgrade_eff, item, item_eff))
                        else:
                            if item_eff.affinity_level > upgrade_eff.affinity_level:
                                possible_upgrades.append((upgrade_item, upgrade_eff, item, item_eff))
                                
    results = defaultdict(lambda: defaultdict(list))
    for upgrade_item, upgrade_eff, item, item_eff in possible_upgrades:
        results[f'{upgrade_item.name} (lvl{upgrade_item.level})'][repr(upgrade_eff)].append((item, item_eff))
        
    for upgrade_item, effects in results.items():
        print(upgrade_item)
        for effect, items in effects.items():
            print('--', effect)
            for item, item_eff in sorted(items, key=lambda i: repr(i[1]), reverse=True):
                item.set_marker(Item.OUTPUT_MARKER)
                print(f'---- {item.name} (lvl{item.level}) - {repr(item_eff)}')
                
    #for upgrade_item, upgrade_eff, item, item_eff in possible_upgrades:
    #    item.locked = True
    #    print(f'{upgrade_item.name} (lvl{upgrade_item.level}) - {repr(upgrade_eff)} <-- {item.name} (lvl{item.level}) - {repr(item_eff)}')


@main.command()
def filter_inventory() -> None:   
    
    print('''
Please ensure that Stranger of Paradise: Final Fantasy Origin is running and you have loaded your save.

***********************************************************************************
* NOTE: All items will be unlocked, and then the items to be kept will be locked. *
* If you don't want your locked items to be changed, press Ctrl+C to cancel now.  *
***********************************************************************************
''')
    try:
        input('(continue)')
    except EOFError:
        print('\nCancelled.')
        return

    inv = Inventory.from_process()
    #inv = Inventory.from_file(Path('inv.bin'))
    
    for item in inv.items:
        item.set_marker(Item.OUTPUT_MARKER)
    
    for item in inv.filter():
        item.unset_marker(Item.OUTPUT_MARKER)
        
    inv.save(Path('inv.bin'))
    create_db(inv)

    print('You can now dismantle all unlocked items from within the game.')
    input('(done)')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input('\n(close)')
