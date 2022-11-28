from memory import Inventory, Item, Effect
from collections import defaultdict
from database import Database, Strings
from pathlib import Path
import csv
import sqlite3

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

def main() -> None:   
    
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
    
    print('Unlocking all items...')
    for item in inv.items:
        item.locked = False

    print('Locking items to be kept...')
    for item in inv.filter():
        item.locked = True
        
    create_db(inv)

    print('You can now dismantle all unlocked items from within the game.')
    input('(done)')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input('\n(close)')
