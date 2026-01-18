using System;
using Game.InventorySystem;
using NUnit.Framework;

namespace Game.Tests.Editor
{
    [TestFixture]
    public class InventoryTests
    {
        private Inventory _inventory;

        [SetUp]
        public void SetUp()
        {
            _inventory = new Inventory(maxSlots: 5, maxStackSize: 10);
        }

        #region AddItem Tests

        [Test]
        public void AddItem_IncreasesSlotCount_WhenNewItem()
        {
            _inventory.AddItem("potion", 1);

            Assert.AreEqual(1, _inventory.SlotCount);
            Assert.AreEqual(1, _inventory.GetItemAmount("potion"));
        }

        [Test]
        public void AddItem_StacksWithExisting_WhenSameItem()
        {
            _inventory.AddItem("potion", 3);
            _inventory.AddItem("potion", 2);

            Assert.AreEqual(1, _inventory.SlotCount);
            Assert.AreEqual(5, _inventory.GetItemAmount("potion"));
        }

        [Test]
        public void AddItem_ReturnsOverflow_WhenExceedsMaxStack()
        {
            var overflow = _inventory.AddItem("potion", 15);

            Assert.AreEqual(5, overflow); // 15 - 10 = 5 overflow
            Assert.AreEqual(10, _inventory.GetItemAmount("potion"));
        }

        [Test]
        public void AddItem_ReturnsOverflow_WhenInventoryFull()
        {
            // Fill inventory
            _inventory.AddItem("item1", 1);
            _inventory.AddItem("item2", 1);
            _inventory.AddItem("item3", 1);
            _inventory.AddItem("item4", 1);
            _inventory.AddItem("item5", 1);

            Assert.IsTrue(_inventory.IsFull);

            var overflow = _inventory.AddItem("item6", 5);

            Assert.AreEqual(5, overflow);
            Assert.AreEqual(0, _inventory.GetItemAmount("item6"));
        }

        [Test]
        public void AddItem_ThrowsException_WhenItemIdEmpty()
        {
            Assert.Throws<ArgumentException>(() => _inventory.AddItem("", 1));
            Assert.Throws<ArgumentException>(() => _inventory.AddItem(null, 1));
        }

        [Test]
        public void AddItem_ThrowsException_WhenAmountNotPositive()
        {
            Assert.Throws<ArgumentException>(() => _inventory.AddItem("potion", 0));
            Assert.Throws<ArgumentException>(() => _inventory.AddItem("potion", -1));
        }

        #endregion

        #region RemoveItem Tests

        [Test]
        public void RemoveItem_DecreasesAmount_WhenSufficientItems()
        {
            _inventory.AddItem("potion", 5);

            var success = _inventory.RemoveItem("potion", 3);

            Assert.IsTrue(success);
            Assert.AreEqual(2, _inventory.GetItemAmount("potion"));
        }

        [Test]
        public void RemoveItem_RemovesSlot_WhenAmountReachesZero()
        {
            _inventory.AddItem("potion", 5);

            _inventory.RemoveItem("potion", 5);

            Assert.AreEqual(0, _inventory.SlotCount);
            Assert.AreEqual(0, _inventory.GetItemAmount("potion"));
        }

        [Test]
        public void RemoveItem_ReturnsFalse_WhenInsufficientItems()
        {
            _inventory.AddItem("potion", 3);

            var success = _inventory.RemoveItem("potion", 5);

            Assert.IsFalse(success);
            Assert.AreEqual(3, _inventory.GetItemAmount("potion")); // Unchanged
        }

        [Test]
        public void RemoveItem_ReturnsFalse_WhenItemNotExists()
        {
            var success = _inventory.RemoveItem("nonexistent", 1);

            Assert.IsFalse(success);
        }

        #endregion

        #region HasItem Tests

        [Test]
        public void HasItem_ReturnsTrue_WhenSufficientAmount()
        {
            _inventory.AddItem("potion", 5);

            Assert.IsTrue(_inventory.HasItem("potion", 5));
            Assert.IsTrue(_inventory.HasItem("potion", 3));
            Assert.IsTrue(_inventory.HasItem("potion", 1));
        }

        [Test]
        public void HasItem_ReturnsFalse_WhenInsufficientAmount()
        {
            _inventory.AddItem("potion", 3);

            Assert.IsFalse(_inventory.HasItem("potion", 5));
        }

        [Test]
        public void HasItem_ReturnsFalse_WhenItemNotExists()
        {
            Assert.IsFalse(_inventory.HasItem("nonexistent"));
        }

        #endregion

        #region GetAllItems Tests

        [Test]
        public void GetAllItems_ReturnsAllSlots()
        {
            _inventory.AddItem("potion", 3);
            _inventory.AddItem("sword", 1);

            var items = _inventory.GetAllItems();

            Assert.AreEqual(2, items.Count);
        }

        [Test]
        public void GetAllItems_ReturnsEmptyList_WhenEmpty()
        {
            var items = _inventory.GetAllItems();

            Assert.AreEqual(0, items.Count);
        }

        #endregion

        #region Clear Tests

        [Test]
        public void Clear_RemovesAllItems()
        {
            _inventory.AddItem("potion", 5);
            _inventory.AddItem("sword", 1);

            _inventory.Clear();

            Assert.AreEqual(0, _inventory.SlotCount);
            Assert.IsFalse(_inventory.HasItem("potion"));
            Assert.IsFalse(_inventory.HasItem("sword"));
        }

        #endregion

        #region Constructor Tests

        [Test]
        public void Constructor_ThrowsException_WhenMaxSlotsNotPositive()
        {
            Assert.Throws<ArgumentException>(() => new Inventory(maxSlots: 0));
            Assert.Throws<ArgumentException>(() => new Inventory(maxSlots: -1));
        }

        [Test]
        public void Constructor_ThrowsException_WhenMaxStackSizeNotPositive()
        {
            Assert.Throws<ArgumentException>(() => new Inventory(maxSlots: 10, maxStackSize: 0));
        }

        #endregion
    }
}
