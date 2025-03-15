<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\TelegramAuthController;

Route::get('/', function () {
    return view('welcome');
});

Route::post('/auth/telegram/callback', [TelegramAuthController::class, 'handleTelegramCallback'])
    ->name('telegram.callback')
    ->middleware('web');

Route::get('/login/telegram', function () {
    return view('telegram-auth');
})->name('login.telegram');
