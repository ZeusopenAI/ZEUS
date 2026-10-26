package com.zeus.keyboard.ui;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.zeus.keyboard.R;

/**
 * Settings Activity - Màn hình cài đặt Zeus AI Keyboard.
 */
public class SettingsActivity extends AppCompatActivity {

    private EditText mApiUrl;
    private EditText mApiKey;
    private EditText mModel;
    private Switch mTelexSwitch;
    private TextView mStatusText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        mApiUrl = findViewById(R.id.edit_api_url);
        mApiKey = findViewById(R.id.edit_api_key);
        mModel = findViewById(R.id.edit_model);
        mTelexSwitch = findViewById(R.id.switch_telex);
        mStatusText = findViewById(R.id.text_status);

        loadSettings();
        setupButtons();
        updateStatus();
    }

    private void loadSettings() {
        SharedPreferences prefs = getSharedPreferences("zeus_keyboard_prefs", MODE_PRIVATE);
        mApiUrl.setText(prefs.getString("ai_api_url", "https://openrouter.ai/api/v1/chat/completions"));
        mApiKey.setText(prefs.getString("ai_api_key", ""));
        mModel.setText(prefs.getString("ai_model", "openai/gpt-4o-mini"));
        mTelexSwitch.setChecked(prefs.getBoolean("telex_enabled", true));
    }

    private void saveSettings() {
        SharedPreferences prefs = getSharedPreferences("zeus_keyboard_prefs", MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();
        editor.putString("ai_api_url", mApiUrl.getText().toString().trim());
        editor.putString("ai_api_key", mApiKey.getText().toString().trim());
        editor.putString("ai_model", mModel.getText().toString().trim());
        editor.putBoolean("telex_enabled", mTelexSwitch.isChecked());
        editor.apply();
        Toast.makeText(this, "Đã lưu cài đặt!", Toast.LENGTH_SHORT).show();
        updateStatus();
    }

    private void setupButtons() {
        Button btnSave = findViewById(R.id.btn_save);
        btnSave.setOnClickListener(v -> saveSettings());

        Button btnEnableKeyboard = findViewById(R.id.btn_enable_keyboard);
        btnEnableKeyboard.setOnClickListener(v -> {
            Intent intent = new Intent(Settings.ACTION_INPUT_METHOD_SETTINGS);
            startActivity(intent);
        });

        Button btnSelectKeyboard = findViewById(R.id.btn_select_keyboard);
        btnSelectKeyboard.setOnClickListener(v -> {
            // Hằng ACTION_SHOW_INPUT_METHOD_PICKER không có trong lớp Settings;
            // cách chuẩn là gọi InputMethodManager.showInputMethodPicker().
            InputMethodManager imm =
                    (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (imm != null) {
                imm.showInputMethodPicker();
            }
        });

        // Telex switch listener
        mTelexSwitch.setOnCheckedChangeListener((buttonView, isChecked) -> {
            SharedPreferences prefs = getSharedPreferences("zeus_keyboard_prefs", MODE_PRIVATE);
            prefs.edit().putBoolean("telex_enabled", isChecked).apply();
        });
    }

    private void updateStatus() {
        SharedPreferences prefs = getSharedPreferences("zeus_keyboard_prefs", MODE_PRIVATE);
        String apiKey = prefs.getString("ai_api_key", "");

        if (apiKey.isEmpty()) {
            mStatusText.setText("⚠️ AI chưa được cấu hình. Thêm API Key để bật tính năng AI.");
            mStatusText.setTextColor(0xFFFF9800);
        } else {
            mStatusText.setText("✅ Zeus AI Keyboard đã sẵn sàng! Nhấn nút ⚡AI trên bàn phím để dùng.");
            mStatusText.setTextColor(0xFF4CAF50);
        }
    }
}
