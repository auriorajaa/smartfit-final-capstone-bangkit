package com.example.smartfit

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.example.smartfit.databinding.ActivityChooseBinding
import com.yalantis.ucrop.UCrop
import java.io.File
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*

class ChooseActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChooseBinding
    private var currentPhotoPath: String? = null
    private var currentImageUri: Uri? = null
    private var pendingPermissionAction: (() -> Unit)? = null

    private val launcherIntentCamera = registerForActivityResult(ActivityResultContracts.TakePicture()) { isSuccess ->
        if (isSuccess) {
            currentImageUri?.let { startCropActivity(it) }
        } else {
            showAlertDialog("Error", "Failed to capture image.")
        }
    }

    private val launcherGallery = registerForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri: Uri? ->
        if (uri != null) {
            startCropActivity(uri)
        } else {
            showAlertDialog("Error", "No image selected from gallery.")
        }
    }

    private val requestPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { permissions ->
        permissions.forEach { (permission, granted) ->
            Log.d("ChooseActivity", "Permission: $permission, Granted: $granted")
        }
        if (permissions.all { it.value }) {
            pendingPermissionAction?.invoke()
            pendingPermissionAction = null
        } else {
            showAlertDialog("Permission Denied", "Please allow the necessary permissions.")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChooseBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.cameraButton.setOnClickListener {
            if (checkAndRequestPermissions(arrayOf(Manifest.permission.CAMERA))) {
                dispatchTakePictureIntent()
            } else {
                pendingPermissionAction = { dispatchTakePictureIntent() }
            }
        }

        binding.galleryButton.setOnClickListener {
            val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                arrayOf(Manifest.permission.READ_MEDIA_IMAGES)
            } else {
                arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
            }

            if (checkAndRequestPermissions(permissions)) {
                launcherGallery.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            } else {
                pendingPermissionAction = { launcherGallery.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }
            }
        }
    }

    private fun checkAndRequestPermissions(permissions: Array<String>): Boolean {
        val neededPermissions = permissions.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        return if (neededPermissions.isNotEmpty()) {
            Log.d("ChooseActivity", "Requesting permissions: ${neededPermissions.joinToString()}")
            requestPermissionLauncher.launch(neededPermissions.toTypedArray())
            false
        } else {
            true
        }
    }

    private fun showAlertDialog(title: String, message: String) {
        AlertDialog.Builder(this).apply {
            setTitle(title)
            setMessage(message)
            setPositiveButton("OK") { dialog, _ -> dialog.dismiss() }
            create().show()
        }
    }

    private fun dispatchTakePictureIntent() {
        val photoFile = try { createImageFile() } catch (ex: IOException) {
            showAlertDialog("Error", "Could not create file for photo: ${ex.message}")
            null
        }

        photoFile?.let {
            val photoURI = FileProvider.getUriForFile(this, "com.example.smartfit.fileprovider", it)
            currentImageUri = photoURI
            launcherIntentCamera.launch(photoURI)
        }
    }

    @Throws(IOException::class)
    private fun createImageFile(): File {
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val storageDir = getExternalFilesDir(null)!!
        return File.createTempFile("JPEG_${timeStamp}_", ".jpg", storageDir).apply { currentPhotoPath = absolutePath }
    }

    private fun startCropActivity(uri: Uri) {
        val destinationUri = Uri.fromFile(File(cacheDir, "cropped"))
        UCrop.of(uri, destinationUri)
            .withAspectRatio(1f, 1f)
            .withMaxResultSize(1000, 1000)
            .start(this)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == RESULT_OK) {
            when (requestCode) {
                UCrop.REQUEST_CROP -> {
                    val resultUri = UCrop.getOutput(data!!)
                    resultUri?.let {
                        val intent = Intent(this, ScanActivity::class.java).apply {
                            putExtra("CROPPED_IMAGE_URI", it.toString())
                        }
                        startActivity(intent)
                    }
                }
                UCrop.RESULT_ERROR -> {
                    UCrop.getError(data!!)?.let { showAlertDialog("Crop Error", it.message ?: "Unknown error occurred.") }
                }
            }
        }
    }

    companion object {
        private const val PERMISSION_REQUEST_CODE = 1001
    }
}
