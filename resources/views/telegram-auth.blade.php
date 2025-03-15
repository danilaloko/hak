<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход через Telegram</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <style>
        /* Существующие стили остаются без изменений */
    </style>
</head>
<body>
    <div class="auth-container">
        <h1 class="auth-title">Добро пожаловать</h1>
        <p class="auth-description">Войдите с помощью вашего аккаунта Telegram</p>
        
        <div class="telegram-login">
            <script async 
                src="https://telegram.org/js/telegram-widget.js"
                data-telegram-login="{{ config('services.telegram.bot_username') }}"
                data-size="large"
                data-onauth="onTelegramAuth(user)"
                data-request-access="write">
            </script>
        </div>

        <div id="auth-status" style="display: none; margin-top: 1rem;"></div>
    </div>

    <script>
        function onTelegramAuth(user) {
            fetch('{{ route('telegram.callback') }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify(user)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.redirect || '/dashboard';
                } else {
                    const statusDiv = document.getElementById('auth-status');
                    statusDiv.style.display = 'block';
                    statusDiv.style.color = '#dc3545';
                    statusDiv.textContent = data.message || 'Ошибка авторизации';
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
            });
        }
    </script>
</body>
</html> 