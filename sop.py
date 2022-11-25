from memory import Inventory


def diff(a, b):
    result = []
    for ac, bc in zip(a, b):
        if ac == bc:
            result.append(ac)
        else:
            result.append('\033[31m' + bc + '\033[39m')
    return ''.join(result)


def main():
    print(
        'Please ensure that Stranger of Paradise: Final Fantasy Origin is running and you have loaded your save.'
    )
    input('(continue)')

    inv = Inventory.from_process()
    print('Unlocking all items...')
    for item in inv.items:
        item.locked = False

    print('Locking items to be kept...')
    for item in inv.filter():
        item.locked = True

    print('You can now dismantle all unlocked items from within the game.')
    input('(continue)')


if __name__ == '__main__':
    main()
