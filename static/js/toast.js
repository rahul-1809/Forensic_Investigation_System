// Simple toast system: reads server-flashed messages rendered into #toast-data
// and displays transient toasts in #toast-container.
(function(){
	if (window.__toasts_initialized) return; // idempotent guard
	window.__toasts_initialized = true;

	function createToast(text, category){
		const container = document.getElementById('toast-container');
		if(!container) return;
		const el = document.createElement('div');
		el.className = 'toast';
		if(category) el.classList.add('toast-' + category);
		el.innerHTML = `
			<div class="toast-body">${text}</div>
			<button class="toast-close" aria-label="close">×</button>
		`;
		container.appendChild(el);

		// entrance animation
		requestAnimationFrame(()=> el.classList.add('show'));

		// close handler
		el.querySelector('.toast-close').addEventListener('click', ()=> {
			hideToast(el);
		});

		// auto dismiss after 4s
		setTimeout(()=> hideToast(el), 4000);
	}

	function hideToast(el){
		if(!el) return;
		el.classList.remove('show');
		el.classList.add('hide');
		setTimeout(()=> el.remove(), 300);
	}

	function initFromServerData(){
		const dataParent = document.getElementById('toast-data');
		if(!dataParent) return;
		const msgs = Array.from(dataParent.querySelectorAll('.toast-data'));
		msgs.forEach(m => {
			const cat = m.getAttribute('data-category') || 'info';
			const text = m.textContent || '';
			createToast(text, cat);
		});
		// remove the data nodes so flashes don't render twice if templates also printed them
		dataParent.remove();
	}

	if (document.readyState === 'loading'){
		document.addEventListener('DOMContentLoaded', initFromServerData);
	} else {
		initFromServerData();
	}

	// expose small API if other scripts want to show toasts programmatically
	window.showToast = function(message, category){ createToast(message, category || 'info'); };
})();

