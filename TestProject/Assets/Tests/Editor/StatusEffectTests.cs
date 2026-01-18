using System;
using Game.Combat;
using NUnit.Framework;

namespace Game.Tests.Editor
{
    [TestFixture]
    public class StatusEffectTests
    {
        private StatusEffectManager _manager;

        [SetUp]
        public void SetUp()
        {
            _manager = new StatusEffectManager();
        }

        #region Red Phase - These tests will fail initially

        [Test]
        public void AddEffect_AppliesAttackBuff()
        {
            var effect = new StatusEffect("attack_up", StatType.Attack, 10f, duration: 5f);

            _manager.AddEffect(effect);

            Assert.AreEqual(10f, _manager.GetStatModifier(StatType.Attack));
        }

        [Test]
        public void AddEffect_StacksMultipleBuffs()
        {
            _manager.AddEffect(new StatusEffect("attack_up_1", StatType.Attack, 10f, duration: 5f));
            _manager.AddEffect(new StatusEffect("attack_up_2", StatType.Attack, 5f, duration: 5f));

            Assert.AreEqual(15f, _manager.GetStatModifier(StatType.Attack));
        }

        [Test]
        public void AddEffect_AppliesDebuff_NegativeValue()
        {
            var effect = new StatusEffect("defense_down", StatType.Defense, -20f, duration: 3f);

            _manager.AddEffect(effect);

            Assert.AreEqual(-20f, _manager.GetStatModifier(StatType.Defense));
        }

        [Test]
        public void Update_RemovesExpiredEffects()
        {
            var effect = new StatusEffect("short_buff", StatType.Attack, 10f, duration: 1f);
            _manager.AddEffect(effect);

            _manager.Update(deltaTime: 2f); // 2秒経過

            Assert.AreEqual(0f, _manager.GetStatModifier(StatType.Attack));
        }

        [Test]
        public void Update_KeepsActiveEffects()
        {
            var effect = new StatusEffect("long_buff", StatType.Attack, 10f, duration: 5f);
            _manager.AddEffect(effect);

            _manager.Update(deltaTime: 2f); // 2秒経過（まだ3秒残っている）

            Assert.AreEqual(10f, _manager.GetStatModifier(StatType.Attack));
        }

        [Test]
        public void RemoveEffect_RemovesSpecificEffect()
        {
            _manager.AddEffect(new StatusEffect("buff_1", StatType.Attack, 10f, duration: 5f));
            _manager.AddEffect(new StatusEffect("buff_2", StatType.Attack, 5f, duration: 5f));

            _manager.RemoveEffect("buff_1");

            Assert.AreEqual(5f, _manager.GetStatModifier(StatType.Attack));
        }

        [Test]
        public void HasEffect_ReturnsTrue_WhenEffectExists()
        {
            _manager.AddEffect(new StatusEffect("poison", StatType.Health, -5f, duration: 10f));

            Assert.IsTrue(_manager.HasEffect("poison"));
        }

        [Test]
        public void HasEffect_ReturnsFalse_WhenEffectNotExists()
        {
            Assert.IsFalse(_manager.HasEffect("nonexistent"));
        }

        [Test]
        public void Clear_RemovesAllEffects()
        {
            _manager.AddEffect(new StatusEffect("buff_1", StatType.Attack, 10f, duration: 5f));
            _manager.AddEffect(new StatusEffect("buff_2", StatType.Defense, 5f, duration: 5f));

            _manager.Clear();

            Assert.AreEqual(0f, _manager.GetStatModifier(StatType.Attack));
            Assert.AreEqual(0f, _manager.GetStatModifier(StatType.Defense));
        }

        [Test]
        public void GetRemainingDuration_ReturnsCorrectTime()
        {
            _manager.AddEffect(new StatusEffect("timed_buff", StatType.Attack, 10f, duration: 5f));

            _manager.Update(deltaTime: 2f);

            Assert.AreEqual(3f, _manager.GetRemainingDuration("timed_buff"), 0.01f);
        }

        #endregion
    }
}
