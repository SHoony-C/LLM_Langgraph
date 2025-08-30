// This file is no longer needed since all functionality has been integrated into the App.vue with a single left sidebar for conversations.
// We're keeping this file empty as a placeholder in case it's referenced elsewhere, but it won't be used in the UI.

<template>
  <div class="redirect-page">
    <p>This view is no longer used. Redirecting to home...</p>
  </div>
</template>

<script>
export default {
  name: 'ChatHistoryPage',
  mounted() {
    // Redirect to home when this component is loaded
    this.$router.push('/');
  }
};
</script>

<style scoped>
.redirect-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--light-text);
}
</style> 