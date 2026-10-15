<script setup>
// "Viewing: <player> ▾" — switch whose picks/stats you're looking at.
defineProps({ players: Array, modelValue: Number, label: { type: String, default: 'Viewing' } })
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="picker">
    <span class="k">{{ label }}</span>
    <select :value="modelValue" @change="$emit('update:modelValue', Number($event.target.value))">
      <option v-for="p in players" :key="p.id" :value="p.id">{{ p.displayName }}{{ p.me ? ' (you)' : '' }}</option>
    </select>
  </label>
</template>

<style scoped>
.picker { display: inline-flex; align-items: center; gap: 8px; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 4px 4px 4px 12px; max-width: 100%; }
.k { font-size: .66rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: #94a3b8; }
select {
  border: 0; background: #f1f5f9; border-radius: 9px; padding: 7px 30px 7px 10px; font: inherit; font-weight: 700; color: #0f172a;
  cursor: pointer; min-width: 0; max-width: 60vw; appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, #64748b 50%), linear-gradient(135deg, #64748b 50%, transparent 50%);
  background-position: calc(100% - 15px) 52%, calc(100% - 10px) 52%; background-size: 5px 5px; background-repeat: no-repeat;
}
select:focus-visible { outline: 2px solid #93c5fd; }
</style>
