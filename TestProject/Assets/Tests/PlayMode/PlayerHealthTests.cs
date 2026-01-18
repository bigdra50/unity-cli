using System.Collections;
using Game.Player;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Game.Tests.PlayMode
{
    [TestFixture]
    public class PlayerHealthTests
    {
        private GameObject _playerObject;
        private PlayerHealth _health;

        [SetUp]
        public void SetUp()
        {
            _playerObject = new GameObject("TestPlayer");
            _health = _playerObject.AddComponent<PlayerHealth>();
        }

        [TearDown]
        public void TearDown()
        {
            Object.Destroy(_playerObject);
        }

        #region Basic Health Tests

        [Test]
        public void Awake_InitializesHealthToMax()
        {
            Assert.AreEqual(100f, _health.CurrentHealth);
            Assert.AreEqual(100f, _health.MaxHealth);
            Assert.AreEqual(1f, _health.HealthPercent);
        }

        [Test]
        public void TakeDamage_ReducesHealth()
        {
            _health.TakeDamage(30f);

            Assert.AreEqual(70f, _health.CurrentHealth, 0.01f);
            Assert.IsTrue(_health.IsAlive);
        }

        [Test]
        public void TakeDamage_FiresEvent()
        {
            float damageReceived = 0f;
            _health.OnDamaged += (amount) => damageReceived = amount;

            _health.TakeDamage(25f);

            Assert.AreEqual(25f, damageReceived);
        }

        [Test]
        public void TakeDamage_IgnoresZeroOrNegative()
        {
            _health.TakeDamage(0f);
            Assert.AreEqual(100f, _health.CurrentHealth);

            _health.TakeDamage(-10f);
            Assert.AreEqual(100f, _health.CurrentHealth);
        }

        [Test]
        public void Heal_RestoresHealth()
        {
            _health.TakeDamage(50f);

            _health.Heal(20f);

            Assert.AreEqual(70f, _health.CurrentHealth, 0.01f);
        }

        [Test]
        public void Heal_DoesNotExceedMax()
        {
            _health.TakeDamage(10f);

            _health.Heal(50f);

            Assert.AreEqual(100f, _health.CurrentHealth);
        }

        [Test]
        public void Heal_FiresEventWithActualAmount()
        {
            _health.TakeDamage(10f);
            float healedAmount = 0f;
            _health.OnHealed += (amount) => healedAmount = amount;

            _health.Heal(50f); // Only 10 can be healed

            Assert.AreEqual(10f, healedAmount, 0.01f);
        }

        #endregion

        #region Death Tests

        [Test]
        public void TakeDamage_DiesWhenHealthReachesZero()
        {
            bool deathFired = false;
            _health.OnDeath += () => deathFired = true;

            _health.TakeDamage(100f);

            Assert.IsFalse(_health.IsAlive);
            Assert.IsTrue(deathFired);
            Assert.AreEqual(0f, _health.CurrentHealth);
        }

        [Test]
        public void TakeDamage_IgnoredWhenDead()
        {
            _health.TakeDamage(100f); // Die

            _health.TakeDamage(50f); // Should be ignored

            Assert.AreEqual(0f, _health.CurrentHealth);
        }

        [Test]
        public void Heal_IgnoredWhenDead()
        {
            _health.TakeDamage(100f); // Die

            _health.Heal(50f);

            Assert.AreEqual(0f, _health.CurrentHealth);
        }

        [Test]
        public void Revive_RestoresHealthAndLife()
        {
            _health.TakeDamage(100f);
            bool reviveFired = false;
            _health.OnRevived += () => reviveFired = true;

            _health.Revive(0.5f); // Revive at 50% health

            Assert.IsTrue(_health.IsAlive);
            Assert.IsTrue(reviveFired);
            Assert.AreEqual(50f, _health.CurrentHealth, 0.01f);
        }

        #endregion

        #region Invincibility Tests (Coroutine-based)

        [UnityTest]
        public IEnumerator TakeDamage_GrantsInvincibility()
        {
            _health.SetInvincibilityDuration(0.5f);

            _health.TakeDamage(10f);

            Assert.IsTrue(_health.IsInvincible);
            yield return null;
        }

        [UnityTest]
        public IEnumerator Invincibility_BlocksSubsequentDamage()
        {
            _health.SetInvincibilityDuration(0.5f);

            _health.TakeDamage(10f); // Triggers invincibility
            _health.TakeDamage(10f); // Should be blocked

            Assert.AreEqual(90f, _health.CurrentHealth, 0.01f);
            yield return null;
        }

        [UnityTest]
        public IEnumerator Invincibility_ExpiresAfterDuration()
        {
            _health.SetInvincibilityDuration(0.2f);

            _health.TakeDamage(10f);
            Assert.IsTrue(_health.IsInvincible);

            yield return new WaitForSeconds(0.3f);

            Assert.IsFalse(_health.IsInvincible);
        }

        [UnityTest]
        public IEnumerator Invincibility_AllowsDamageAfterExpiry()
        {
            _health.SetInvincibilityDuration(0.1f);

            _health.TakeDamage(10f); // 90 HP, invincible

            yield return new WaitForSeconds(0.15f);

            _health.TakeDamage(10f); // Should work now

            Assert.AreEqual(80f, _health.CurrentHealth, 0.01f);
        }

        #endregion

        #region Regeneration Tests (Time-based)

        [UnityTest]
        public IEnumerator Regeneration_StartsAfterDelay()
        {
            _health.SetRegeneration(rate: 50f, delay: 0.2f);
            _health.TakeDamage(50f); // 50 HP

            // Wait past invincibility but before regen delay
            yield return new WaitForSeconds(0.1f);
            Assert.IsFalse(_health.IsRegenerating);

            // Wait past regen delay
            yield return new WaitForSeconds(0.2f);
            Assert.IsTrue(_health.IsRegenerating);
        }

        [UnityTest]
        public IEnumerator Regeneration_RestoresHealthOverTime()
        {
            _health.SetRegeneration(rate: 100f, delay: 0.1f);
            _health.SetInvincibilityDuration(0.05f);
            _health.TakeDamage(50f); // 50 HP

            yield return new WaitForSeconds(0.5f);

            // Should have regenerated significantly
            Assert.Greater(_health.CurrentHealth, 70f);
        }

        [UnityTest]
        public IEnumerator Regeneration_StopsWhenDamaged()
        {
            _health.SetRegeneration(rate: 50f, delay: 0.1f);
            _health.SetInvincibilityDuration(0.05f);
            _health.TakeDamage(30f);

            yield return new WaitForSeconds(0.15f);
            Assert.IsTrue(_health.IsRegenerating);

            yield return new WaitForSeconds(0.1f);
            _health.TakeDamage(10f);

            Assert.IsFalse(_health.IsRegenerating);
        }

        [UnityTest]
        public IEnumerator Regeneration_StopsAtMaxHealth()
        {
            _health.SetRegeneration(rate: 200f, delay: 0.05f);
            _health.SetInvincibilityDuration(0.02f);
            _health.TakeDamage(10f);

            yield return new WaitForSeconds(0.3f);

            Assert.AreEqual(100f, _health.CurrentHealth, 0.01f);
            Assert.IsFalse(_health.IsRegenerating);
        }

        #endregion
    }
}
