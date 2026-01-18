using System;
using Game.Combat;
using NUnit.Framework;

namespace Game.Tests.Editor
{
    [TestFixture]
    public class DamageCalculatorTests
    {
        [Test]
        public void Calculate_NoDamageReduction_WhenDefenseIsZero()
        {
            var result = DamageCalculator.Calculate(baseDamage: 100f, defense: 0f);

            Assert.AreEqual(100f, result, 0.01f);
        }

        [Test]
        public void Calculate_HalvesDamage_WhenDefenseEquals100()
        {
            // defense / (defense + 100) = 100 / 200 = 0.5 reduction
            var result = DamageCalculator.Calculate(baseDamage: 100f, defense: 100f);

            Assert.AreEqual(50f, result, 0.01f);
        }

        [Test]
        public void Calculate_AppliesCriticalMultiplier_WhenCritical()
        {
            var normal = DamageCalculator.Calculate(baseDamage: 100f, defense: 0f, isCritical: false);
            var critical = DamageCalculator.Calculate(baseDamage: 100f, defense: 0f, isCritical: true);

            Assert.AreEqual(100f, normal, 0.01f);
            Assert.AreEqual(150f, critical, 0.01f);
            Assert.AreEqual(DamageCalculator.CriticalMultiplier, critical / normal, 0.01f);
        }

        [Test]
        public void Calculate_AppliesElementalModifier()
        {
            var normal = DamageCalculator.Calculate(baseDamage: 100f, defense: 0f, elementalModifier: 1f);
            var weak = DamageCalculator.Calculate(baseDamage: 100f, defense: 0f, elementalModifier: 2f);
            var resist = DamageCalculator.Calculate(baseDamage: 100f, defense: 0f, elementalModifier: 0.5f);

            Assert.AreEqual(100f, normal, 0.01f);
            Assert.AreEqual(200f, weak, 0.01f);
            Assert.AreEqual(50f, resist, 0.01f);
        }

        [Test]
        public void Calculate_CombinesAllModifiers()
        {
            // base=100, defense=100 (50% reduction), critical (1.5x), elemental=2x
            // 100 * 0.5 * 1.5 * 2 = 150
            var result = DamageCalculator.Calculate(
                baseDamage: 100f,
                defense: 100f,
                isCritical: true,
                elementalModifier: 2f);

            Assert.AreEqual(150f, result, 0.01f);
        }

        [Test]
        public void Calculate_ReturnsMinDamage_WhenResultWouldBeTooLow()
        {
            // Very high defense should still deal minimum damage
            var result = DamageCalculator.Calculate(baseDamage: 1f, defense: 10000f);

            Assert.AreEqual(DamageCalculator.MinDamage, result);
        }

        [Test]
        public void Calculate_ThrowsException_WhenBaseDamageIsNegative()
        {
            Assert.Throws<ArgumentException>(() =>
                DamageCalculator.Calculate(baseDamage: -10f, defense: 0f));
        }

        [Test]
        public void Calculate_ThrowsException_WhenDefenseIsNegative()
        {
            Assert.Throws<ArgumentException>(() =>
                DamageCalculator.Calculate(baseDamage: 100f, defense: -10f));
        }

        [Test]
        public void CalculateEffectiveHP_ReturnsHP_WhenDefenseIsZero()
        {
            var result = DamageCalculator.CalculateEffectiveHP(hp: 100f, defense: 0f);

            Assert.AreEqual(100f, result, 0.01f);
        }

        [Test]
        public void CalculateEffectiveHP_DoublesHP_WhenDefenseIs100()
        {
            // Effective HP = HP * (1 + defense/100) = 100 * 2 = 200
            var result = DamageCalculator.CalculateEffectiveHP(hp: 100f, defense: 100f);

            Assert.AreEqual(200f, result, 0.01f);
        }
    }
}
