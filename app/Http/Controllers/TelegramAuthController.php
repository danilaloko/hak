<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class TelegramAuthController extends Controller
{
    public function handleTelegramCallback(Request $request)
    {
        $telegramData = $request->all();
        
        try {
            $user = User::where('telegram_id', $telegramData['id'])->first();

            if (!$user) {
                $user = User::create([
                    'name' => $telegramData['first_name'] ?? $telegramData['username'],
                    'email' => $telegramData['id'] . '@telegram.com',
                    'password' => Hash::make(Str::random(16)),
                    'telegram_id' => $telegramData['id'],
                    'telegram_username' => $telegramData['username'] ?? null,
                ]);
            }

            Auth::login($user);

            return response()->json([
                'success' => true,
                'redirect' => $request->get('redirect_url', '/dashboard')
            ]);

        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Ошибка авторизации: ' . $e->getMessage()
            ], 422);
        }
    }

    private function checkTelegramAuthorization($auth_data) 
    {
        $check_hash = $auth_data['hash'];
        unset($auth_data['hash']);
        
        $data_check_arr = [];
        
        foreach ($auth_data as $key => $value) {
            $data_check_arr[] = $key . '=' . $value;
        }
        
        sort($data_check_arr);
        
        $data_check_string = implode("\n", $data_check_arr);
        $secret_key = hash('sha256', config('services.telegram.bot_token'), true);
        $hash = hash_hmac('sha256', $data_check_string, $secret_key);
        
        if (strcmp($hash, $check_hash) !== 0) {
            return false;
        }
        
        if ((time() - $auth_data['auth_date']) > 86400) {
            return false;
        }
        
        return $auth_data;
    }
} 