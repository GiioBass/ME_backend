#!/bin/bash
# Script to reset the Mystic Explorers database and world state

echo "⚠️  WARNING: This will delete all player progress and reset the world."
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Stopping servers (if any)..."
    # Note: We can't easily kill remote processes from here reliably without pids, 
    # but we can at least wipe the data.
    
    echo "Deleting database.db..."
    rm -f /var/www/html/ME_backend/database.db
    
    echo "✅ System reset complete. Restart the backend to regenerate the world."
    echo "💡 TIP: The frontend may still have old terminal history in its local storage."
    echo "Refining: Log out in the browser or type 'clear' in the terminal to reset it."
    echo "Use 'me-be' to start the server."
fi
