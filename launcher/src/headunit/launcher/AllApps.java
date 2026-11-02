package headunit.launcher;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AbsListView;
import android.widget.BaseAdapter;
import android.widget.GridView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.text.Collator;
import java.util.ArrayList;
import java.util.List;

/** Every app. Closes when one opens, so the icons do not stay in memory. */
public class AllApps extends Activity {
    private final List<ResolveInfo> apps = new ArrayList<>();
    private Bitmap[] thumbnails;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(Home.BACKGROUND);
        getWindow().setNavigationBarColor(Home.BACKGROUND);

        PackageManager pm = getPackageManager();
        Intent launchable = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        for (ResolveInfo app : pm.queryIntentActivities(launchable, 0)) {
            if (!app.activityInfo.packageName.equals(getPackageName())) {
                apps.add(app);
            }
        }
        Collator order = Collator.getInstance();
        apps.sort((a, b) -> order.compare(a.loadLabel(pm).toString(), b.loadLabel(pm).toString()));
        thumbnails = new Bitmap[apps.size()];

        GridView grid = new GridView(this);
        grid.setBackgroundColor(Home.BACKGROUND);
        grid.setNumColumns(6);
        int gap = Home.dp(this, 12);
        grid.setHorizontalSpacing(gap);
        grid.setVerticalSpacing(gap);
        grid.setPadding(gap, gap, gap, gap);
        grid.setClipToPadding(false);
        grid.setAdapter(new Adapter());
        grid.setOnItemClickListener((parent, view, position, id) -> open(apps.get(position)));
        setContentView(grid);
    }

    private void open(ResolveInfo app) {
        startActivity(new Intent(Intent.ACTION_MAIN)
            .addCategory(Intent.CATEGORY_LAUNCHER)
            .setComponent(new ComponentName(app.activityInfo.packageName, app.activityInfo.name))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED));
        finish();
    }

    private class Adapter extends BaseAdapter {
        @Override
        public int getCount() {
            return apps.size();
        }

        @Override
        public Object getItem(int position) {
            return apps.get(position);
        }

        @Override
        public long getItemId(int position) {
            return position;
        }

        @Override
        public View getView(int position, View recycled, ViewGroup parent) {
            LinearLayout tile = recycled != null ? (LinearLayout) recycled
                : Home.tile(AllApps.this, null, "", 64, 16);
            tile.setLayoutParams(new AbsListView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Home.dp(AllApps.this, 136)));
            ResolveInfo app = apps.get(position);
            PackageManager pm = getPackageManager();
            ((ImageView) tile.getChildAt(0)).setImageBitmap(thumbnail(position, app, pm));
            ((TextView) tile.getChildAt(1)).setText(app.loadLabel(pm));
            return tile;
        }
    }

    /** Keeps only a reduced copy of each icon; the originals are much larger. */
    private Bitmap thumbnail(int position, ResolveInfo app, PackageManager pm) {
        if (thumbnails[position] == null) {
            int side = Home.dp(this, 64);
            Bitmap bitmap = Bitmap.createBitmap(side, side, Bitmap.Config.ARGB_8888);
            Drawable icon = app.loadIcon(pm);
            icon.setBounds(0, 0, side, side);
            icon.draw(new Canvas(bitmap));
            thumbnails[position] = bitmap;
        }
        return thumbnails[position];
    }
}
