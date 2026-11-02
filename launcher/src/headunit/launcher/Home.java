package headunit.launcher;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.os.Bundle;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextClock;
import android.widget.TextView;
import android.widget.Toast;

import java.util.Locale;

/** Home screen: time and date on the left, large shortcuts on the right. */
public class Home extends Activity {
    static final int BACKGROUND = 0xFF0E1013;
    static final int TILE = 0xFF1C2026;
    static final int TEXT = 0xFFF2F4F7;
    static final int TEXT_DIM = 0xFFA6ADB8;

    /** Label and package of each shortcut. Four columns by two rows; the last slot is "Apps". */
    private static final String[][] SHORTCUTS = {
        {"Maps", "com.google.android.apps.maps"},
        {"Waze", "com.waze"},
        {"Spotify", "com.spotify.music"},
        {"Radio", "com.tw.radio"},
        {"Bluetooth", "com.tw.bt"},
        {"Phone", "com.zjinnova.zlink"},
        {"Settings", "com.dofun.carsetting"},
    };
    private static final int COLUMNS = 4;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(BACKGROUND);
        getWindow().setNavigationBarColor(BACKGROUND);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.HORIZONTAL);
        root.setBackgroundColor(BACKGROUND);
        int margin = dp(this, 16);
        root.setPadding(margin, margin, margin, margin);
        root.addView(clock(), new LinearLayout.LayoutParams(dp(this, 320), ViewGroup.LayoutParams.MATCH_PARENT));
        root.addView(shortcuts(), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1));
        setContentView(root);
    }

    /** Already on the home screen, so Back has nowhere to go. */
    @Override
    public void onBackPressed() {
    }

    private View clock() {
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setGravity(Gravity.CENTER_VERTICAL);
        column.setPadding(dp(this, 16), 0, dp(this, 16), 0);

        TextClock time = new TextClock(this);
        time.setFormat12Hour("h:mm");
        time.setFormat24Hour("HH:mm");
        time.setTextSize(88);
        time.setTextColor(TEXT);
        time.setTypeface(Typeface.create("sans-serif-light", Typeface.NORMAL));
        time.setSingleLine(true);
        column.addView(time);

        String pattern = DateFormat.getBestDateTimePattern(Locale.getDefault(), "EEEEMMMMd");
        TextClock date = new TextClock(this);
        date.setFormat12Hour(pattern);
        date.setFormat24Hour(pattern);
        date.setTextSize(24);
        date.setTextColor(TEXT_DIM);
        column.addView(date);
        return column;
    }

    private View shortcuts() {
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        LinearLayout row = null;
        for (int i = 0; i <= SHORTCUTS.length; i++) {
            if (i % COLUMNS == 0) {
                row = new LinearLayout(this);
                rows.addView(row, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
            }
            View tile = i < SHORTCUTS.length ? shortcut(SHORTCUTS[i][0], SHORTCUTS[i][1]) : appsButton();
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
            int gap = dp(this, 8);
            params.setMargins(gap, gap, gap, gap);
            row.addView(tile, params);
        }
        return rows;
    }

    private View shortcut(String label, String packageName) {
        Drawable icon = null;
        try {
            icon = getPackageManager().getApplicationIcon(packageName);
        } catch (PackageManager.NameNotFoundException e) {
            // Not installed: the tile has no icon and says so when tapped.
        }
        View tile = tile(this, icon, label, 96, 24);
        tile.setOnClickListener(v -> open(packageName, label));
        return tile;
    }

    private View appsButton() {
        View tile = tile(this, getDrawable(android.R.drawable.ic_dialog_dialer), "Apps", 96, 24);
        tile.setOnClickListener(v -> startActivity(new Intent(this, AllApps.class)));
        return tile;
    }

    private void open(String packageName, String label) {
        Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
        if (intent == null) {
            Toast.makeText(this, label + " is not available", Toast.LENGTH_SHORT).show();
            return;
        }
        startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    /** Rounded tile with an icon and a label, shared by the shortcuts and the app list. */
    static LinearLayout tile(Context context, Drawable icon, String label, int iconDp, int textSp) {
        LinearLayout tile = new LinearLayout(context);
        tile.setOrientation(LinearLayout.VERTICAL);
        tile.setGravity(Gravity.CENTER);
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(TILE);
        shape.setCornerRadius(dp(context, 16));
        tile.setBackground(new RippleDrawable(ColorStateList.valueOf(0x33FFFFFF), shape, null));

        ImageView image = new ImageView(context);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        image.setImageDrawable(icon);
        tile.addView(image, new LinearLayout.LayoutParams(dp(context, iconDp), dp(context, iconDp)));

        TextView text = new TextView(context);
        text.setText(label);
        text.setTextSize(textSp);
        text.setTextColor(TEXT);
        text.setGravity(Gravity.CENTER);
        text.setSingleLine(true);
        text.setPadding(dp(context, 8), dp(context, 8), dp(context, 8), 0);
        tile.addView(text);
        return tile;
    }

    static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }
}
