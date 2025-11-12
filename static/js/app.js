// UA: Налаштування CSRF для jQuery; EN: CSRF setup for jQuery AJAX
(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
  }

  const csrftoken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || getCookie('csrftoken');

  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      const safeMethod = /^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type);
      if (!safeMethod && !this.crossDomain && csrftoken) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    }
  });

  // EN: Toast helper (Bootstrap 5); UA: Хелпер для тостів
  window.showToast = function (message, type = "primary") {
    const id = "toast-" + Math.random().toString(36).slice(2);
    const html = `
      <div id="${id}" class="toast align-items-center text-bg-${type} border-0 position-fixed bottom-0 end-0 m-3" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body">${message}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el, { delay: 3000 });
    toast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
  };
})();
