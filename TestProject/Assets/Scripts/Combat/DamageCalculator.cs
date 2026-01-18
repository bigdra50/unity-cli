using System;
using UnityEngine;

namespace Game.Combat
{
    /// <summary>
    /// Damage calculation with critical hits, defense reduction, and elemental modifiers
    /// </summary>
    public static class DamageCalculator
    {
        public const float CriticalMultiplier = 1.5f;
        public const float MinDamage = 1f;

        /// <summary>
        /// Calculate final damage after applying defense and modifiers
        /// </summary>
        public static float Calculate(float baseDamage, float defense, bool isCritical = false, float elementalModifier = 1f)
        {
            if (baseDamage < 0) throw new ArgumentException("Base damage cannot be negative", nameof(baseDamage));
            if (defense < 0) throw new ArgumentException("Defense cannot be negative", nameof(defense));
            if (elementalModifier < 0) throw new ArgumentException("Elemental modifier cannot be negative", nameof(elementalModifier));

            // Defense formula: damage reduction = defense / (defense + 100)
            var defenseReduction = defense / (defense + 100f);
            var reducedDamage = baseDamage * (1f - defenseReduction);

            // Apply critical hit
            if (isCritical)
            {
                reducedDamage *= CriticalMultiplier;
            }

            // Apply elemental modifier
            reducedDamage *= elementalModifier;

            // Ensure minimum damage
            return Mathf.Max(reducedDamage, MinDamage);
        }

        /// <summary>
        /// Calculate effective HP considering defense
        /// </summary>
        public static float CalculateEffectiveHP(float hp, float defense)
        {
            if (hp < 0) throw new ArgumentException("HP cannot be negative", nameof(hp));
            if (defense < 0) throw new ArgumentException("Defense cannot be negative", nameof(defense));

            // Effective HP = HP * (1 + defense/100)
            return hp * (1f + defense / 100f);
        }
    }
}
