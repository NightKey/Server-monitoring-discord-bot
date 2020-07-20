"""
Version file:
    curr x.x.x
    server_until x.y.z 
    browser_until x.y.z
    total x.y.z
Creates a version file, after an update created.
"""

try:
    with open('version', 'r') as f:
        data = f.read(-1).split('\n')
        print('Inported')
except Exception as ex:
    print(f'{type(ex)} --> {ex}')
    data = [f'current 0.0.0', 'server_untill 0.0.0', 'browser_untill 0.0.0', 'total 0.0.0']
print(f"Last version: {data[0].split(' ')[1]}")
current = input('Type in the new version (x.y.z): ')
tmp = data[0].split(' ')[-1]
data[0] = f'current {current}'
ansv = str(input('Did anything change with the server since the last update? (Y/[N]) ') or 'N')
if ansv.upper() == 'Y':
    data[1] = f'server_untill {tmp}'
ansv = str(input('Did anything change with the browser since the last update? (Y/[N]) ') or 'N')
if ansv.upper() == 'Y':
    data[2] = f'browser_untill {tmp}'
ansv = str(input('Were there anything requiriing a system restart? (For example changes to the runner.) (Y/[N]) ') or 'N')
if ansv.upper() == 'Y':
    data[3] = f'total {tmp}'
with open('version', 'w') as f:
    for i, line in enumerate(data):
        if i < len(data) - 1:
            f.write(f'{line}\n')
        else:
            f.write(f'{line}')