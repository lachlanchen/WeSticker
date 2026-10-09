package art.lazying.westicker;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WeStickerBillingPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
