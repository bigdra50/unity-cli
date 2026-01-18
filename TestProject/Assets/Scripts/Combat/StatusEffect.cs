using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Combat
{
    public enum StatType
    {
        Attack,
        Defense,
        Health,
        Speed
    }

    public class StatusEffect
    {
        public string Id { get; }
        public StatType StatType { get; }
        public float Value { get; }
        public float Duration { get; }
        public float RemainingTime { get; private set; }

        public bool IsExpired => RemainingTime <= 0f;

        public StatusEffect(string id, StatType statType, float value, float duration)
        {
            Id = id;
            StatType = statType;
            Value = value;
            Duration = duration;
            RemainingTime = duration;
        }

        public void Update(float deltaTime)
        {
            RemainingTime -= deltaTime;
        }
    }

    public class StatusEffectManager
    {
        private readonly List<StatusEffect> _effects = new();

        public event Action<StatusEffect> OnEffectAdded;
        public event Action<StatusEffect> OnEffectRemoved;
        public event Action<StatusEffect> OnEffectExpired;

        public int ActiveEffectCount => _effects.Count;

        public void AddEffect(StatusEffect effect)
        {
            // 同一IDがあれば上書き（リフレッシュ）
            var existing = _effects.FindIndex(e => e.Id == effect.Id);
            if (existing >= 0)
            {
                _effects[existing] = effect;
            }
            else
            {
                _effects.Add(effect);
            }
            OnEffectAdded?.Invoke(effect);
        }

        public void RemoveEffect(string id)
        {
            var effect = _effects.FirstOrDefault(e => e.Id == id);
            if (effect != null)
            {
                _effects.Remove(effect);
                OnEffectRemoved?.Invoke(effect);
            }
        }

        public bool HasEffect(string id)
        {
            return _effects.Any(e => e.Id == id);
        }

        public float GetStatModifier(StatType statType)
        {
            return _effects
                .Where(e => e.StatType == statType)
                .Sum(e => e.Value);
        }

        public float GetRemainingDuration(string id)
        {
            var effect = _effects.FirstOrDefault(e => e.Id == id);
            return effect?.RemainingTime ?? 0f;
        }

        public void Update(float deltaTime)
        {
            foreach (var effect in _effects)
            {
                effect.Update(deltaTime);
            }

            // 期限切れエフェクトを通知して削除
            var expired = _effects.Where(e => e.IsExpired).ToList();
            foreach (var effect in expired)
            {
                OnEffectExpired?.Invoke(effect);
            }
            _effects.RemoveAll(e => e.IsExpired);
        }

        public void Clear()
        {
            _effects.Clear();
        }
    }
}
