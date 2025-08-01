import os

# All directories that need __init__.py files
directories = [
    'wepool_project',
    'users',
    'users/migrations', 
    'users/management',
    'users/management/commands',
    'users/templatetags',
    'dashboard',
    'dashboard/migrations',
    'dashboard/management', 
    'dashboard/management/commands',
    'dashboard/templatetags',
    'core',
    'core/migrations',
    'core/management',
    'core/management/commands', 
    'core/templatetags',
]

for directory in directories:
    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Create __init__.py file
    init_file = os.path.join(directory, '__init__.py')
    with open(init_file, 'w') as f:
        f.write('')  # Empty file
    print(f"Created/verified {init_file}")

print("All __init__.py files created successfully!")
