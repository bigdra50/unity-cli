using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.InventorySystem
{
    /// <summary>
    /// Player inventory with slot management and stacking
    /// </summary>
    public class Inventory
    {
        private readonly Dictionary<string, InventorySlot> _slots = new();
        private readonly int _maxSlots;
        private readonly int _maxStackSize;

        public int SlotCount => _slots.Count;
        public int MaxSlots => _maxSlots;
        public bool IsFull => _slots.Count >= _maxSlots;

        public Inventory(int maxSlots = 20, int maxStackSize = 99)
        {
            if (maxSlots <= 0) throw new ArgumentException("Max slots must be positive", nameof(maxSlots));
            if (maxStackSize <= 0) throw new ArgumentException("Max stack size must be positive", nameof(maxStackSize));

            _maxSlots = maxSlots;
            _maxStackSize = maxStackSize;
        }

        /// <summary>
        /// Add item to inventory. Returns amount that couldn't be added (overflow)
        /// </summary>
        public int AddItem(string itemId, int amount)
        {
            if (string.IsNullOrEmpty(itemId)) throw new ArgumentException("Item ID cannot be empty", nameof(itemId));
            if (amount <= 0) throw new ArgumentException("Amount must be positive", nameof(amount));

            var remaining = amount;

            // Try to stack with existing slot
            if (_slots.TryGetValue(itemId, out var slot))
            {
                var spaceInSlot = _maxStackSize - slot.Amount;
                var toAdd = Math.Min(remaining, spaceInSlot);
                slot.Amount += toAdd;
                remaining -= toAdd;
            }

            // Create new slot if needed and possible
            if (remaining > 0 && !IsFull && !_slots.ContainsKey(itemId))
            {
                var toAdd = Math.Min(remaining, _maxStackSize);
                _slots[itemId] = new InventorySlot(itemId, toAdd);
                remaining -= toAdd;
            }

            return remaining; // Returns overflow
        }

        /// <summary>
        /// Remove item from inventory. Returns true if successful
        /// </summary>
        public bool RemoveItem(string itemId, int amount)
        {
            if (string.IsNullOrEmpty(itemId)) throw new ArgumentException("Item ID cannot be empty", nameof(itemId));
            if (amount <= 0) throw new ArgumentException("Amount must be positive", nameof(amount));

            if (!_slots.TryGetValue(itemId, out var slot) || slot.Amount < amount)
            {
                return false;
            }

            slot.Amount -= amount;
            if (slot.Amount <= 0)
            {
                _slots.Remove(itemId);
            }

            return true;
        }

        /// <summary>
        /// Get amount of specific item in inventory
        /// </summary>
        public int GetItemAmount(string itemId)
        {
            if (string.IsNullOrEmpty(itemId)) return 0;
            return _slots.TryGetValue(itemId, out var slot) ? slot.Amount : 0;
        }

        /// <summary>
        /// Check if inventory contains at least specified amount
        /// </summary>
        public bool HasItem(string itemId, int amount = 1)
        {
            return GetItemAmount(itemId) >= amount;
        }

        /// <summary>
        /// Get all items in inventory
        /// </summary>
        public IReadOnlyList<InventorySlot> GetAllItems()
        {
            return _slots.Values.ToList();
        }

        /// <summary>
        /// Clear all items from inventory
        /// </summary>
        public void Clear()
        {
            _slots.Clear();
        }
    }

    public class InventorySlot
    {
        public string ItemId { get; }
        public int Amount { get; set; }

        public InventorySlot(string itemId, int amount)
        {
            ItemId = itemId;
            Amount = amount;
        }
    }
}
