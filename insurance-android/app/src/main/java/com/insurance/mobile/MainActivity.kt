package com.insurance.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.insurance.mobile.ui.InsuranceRoot
import com.insurance.mobile.ui.theme.InsuranceTheme
import dagger.hilt.android.AndroidEntryPoint

/**
 * Single activity: hosts [InsuranceRoot]. The root graph handles Google
 * Sign-In and gates access to the main shell; this class stays thin.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            InsuranceTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    InsuranceRoot()
                }
            }
        }
    }
}
