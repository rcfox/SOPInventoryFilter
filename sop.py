from memory import Inventory


def diff(a: str, b: str) -> str:
    result = []
    for ac, bc in zip(a, b):
        if ac == bc:
            result.append(ac)
        else:
            result.append('\033[31m' + bc + '\033[39m')
    return ''.join(result)


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
    
    print('Unlocking all items...')
    for item in inv.items:
        item.locked = False

    print('Locking items to be kept...')
    for item in inv.filter():
        item.locked = True

    print('You can now dismantle all unlocked items from within the game.')
    input('(done)')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input('\n(close)')
