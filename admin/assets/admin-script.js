document.addEventListener('DOMContentLoaded', () => {
  const yearNode = document.getElementById('year');
  if (yearNode) {
    yearNode.textContent = new Date().getFullYear();
  }

  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      if (!button) return;

      const label = button.textContent;
      button.textContent = 'Saved';
      button.disabled = true;
      setTimeout(() => {
        button.textContent = label;
        button.disabled = false;
      }, 1500);
    });
  });
});
