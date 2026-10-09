const yearNode = document.getElementById('year');
if (yearNode) {
  yearNode.textContent = new Date().getFullYear();
}

const forms = document.querySelectorAll('form');
forms.forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      const originalText = button.textContent;
      button.textContent = 'Submitted';
      button.disabled = true;
      setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
      }, 1800);
    }
  });
});

const propertyCards = document.querySelectorAll('.listing-card, .property-card');
propertyCards.forEach((card) => {
  card.addEventListener('mouseenter', () => {
    card.style.transform = 'translateY(-4px)';
    card.style.transition = 'transform 0.2s ease';
  });

  card.addEventListener('mouseleave', () => {
    card.style.transform = 'translateY(0)';
  });
});
