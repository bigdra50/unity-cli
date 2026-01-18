using System;
using System.Collections;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Player health component with damage, healing, and death handling.
    /// Supports invincibility frames and regeneration.
    /// </summary>
    public class PlayerHealth : MonoBehaviour
    {
        [SerializeField] private float _maxHealth = 100f;
        [SerializeField] private float _invincibilityDuration = 1f;
        [SerializeField] private float _regenRate = 5f; // HP per second
        [SerializeField] private float _regenDelay = 3f; // Seconds after damage before regen starts

        private float _currentHealth;
        private bool _isInvincible;
        private bool _isDead;
        private float _timeSinceLastDamage;
        private bool _isRegenerating;

        public float CurrentHealth => _currentHealth;
        public float MaxHealth => _maxHealth;
        public float HealthPercent => _currentHealth / _maxHealth;
        public bool IsAlive => !_isDead;
        public bool IsInvincible => _isInvincible;
        public bool IsRegenerating => _isRegenerating;

        public event Action<float> OnDamaged;
        public event Action<float> OnHealed;
        public event Action OnDeath;
        public event Action OnRevived;

        private void Awake()
        {
            _currentHealth = _maxHealth;
        }

        private void Update()
        {
            if (_isDead) return;

            // Regeneration logic
            _timeSinceLastDamage += Time.deltaTime;

            if (_timeSinceLastDamage >= _regenDelay && _currentHealth < _maxHealth)
            {
                _isRegenerating = true;
                Heal(_regenRate * Time.deltaTime);
            }
            else
            {
                _isRegenerating = false;
            }
        }

        public void TakeDamage(float amount)
        {
            if (_isDead || _isInvincible || amount <= 0) return;

            _currentHealth = Mathf.Max(0, _currentHealth - amount);
            _timeSinceLastDamage = 0f;
            _isRegenerating = false;

            OnDamaged?.Invoke(amount);

            if (_currentHealth <= 0)
            {
                Die();
            }
            else
            {
                StartCoroutine(InvincibilityCoroutine());
            }
        }

        public void Heal(float amount)
        {
            if (_isDead || amount <= 0) return;

            var previousHealth = _currentHealth;
            _currentHealth = Mathf.Min(_maxHealth, _currentHealth + amount);

            var actualHealed = _currentHealth - previousHealth;
            if (actualHealed > 0)
            {
                OnHealed?.Invoke(actualHealed);
            }
        }

        public void Revive(float healthPercent = 1f)
        {
            if (!_isDead) return;

            _isDead = false;
            _currentHealth = _maxHealth * Mathf.Clamp01(healthPercent);
            _timeSinceLastDamage = 0f;

            OnRevived?.Invoke();
        }

        public void SetMaxHealth(float maxHealth, bool healToFull = false)
        {
            _maxHealth = Mathf.Max(1f, maxHealth);
            _currentHealth = Mathf.Min(_currentHealth, _maxHealth);

            if (healToFull)
            {
                _currentHealth = _maxHealth;
            }
        }

        private void Die()
        {
            _isDead = true;
            _isInvincible = false;
            _isRegenerating = false;
            StopAllCoroutines();

            OnDeath?.Invoke();
        }

        private IEnumerator InvincibilityCoroutine()
        {
            _isInvincible = true;
            yield return new WaitForSeconds(_invincibilityDuration);
            _isInvincible = false;
        }

        // For testing: allow setting invincibility duration
        public void SetInvincibilityDuration(float duration)
        {
            _invincibilityDuration = duration;
        }

        // For testing: allow setting regen settings
        public void SetRegeneration(float rate, float delay)
        {
            _regenRate = rate;
            _regenDelay = delay;
        }
    }
}
