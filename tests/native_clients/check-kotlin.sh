#!/usr/bin/env bash
set -euo pipefail

# No Gradle, SDK downloads, signing, app packaging or store requests.
if [[ $# -gt 1 || (${1:-} != "" && ${1:-} != "--ui") ]]; then
    printf 'Usage: %s [--ui]\n' "$0" >&2
    exit 2
fi
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cache="${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2/files-2.1"
sdk="${ANDROID_HOME:?Set ANDROID_HOME to an existing Android SDK}"
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT

artifact() {
    local directory="$cache/$1/$2/$3"
    local -a matches=()
    mapfile -t matches < <(rg --files "$directory" -g "*.$4")
    if [[ ${#matches[@]} != 1 ]]; then printf 'Need one cached artifact: %s\n' "$directory" >&2; return 1; fi
    printf '%s' "${matches[0]}"
}
stdlib="$(artifact org.jetbrains.kotlin kotlin-stdlib 2.2.20 jar)"
coroutines="$(artifact org.jetbrains.kotlinx kotlinx-coroutines-core-jvm 1.8.0 jar)"
annotations="$(artifact org.jetbrains annotations 13.0 jar)"
compiler="$(artifact org.jetbrains.kotlin kotlin-compiler-embeddable 2.2.20 jar):$stdlib:$coroutines:$annotations"
compiler+=":$(artifact org.jetbrains.kotlin kotlin-script-runtime 2.2.20 jar)"
compiler+=":$(artifact org.jetbrains.kotlin kotlin-reflect 1.6.10 jar)"
sources="$root/android/app/src/main/java/art/lazying/westicker"
compile=(java -Xmx512m -cp "$compiler" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -jvm-target 17)
"${compile[@]}" -classpath "$stdlib" -d "$temp/recovery.jar" "$sources/BillingRecovery.kt" "$root/tests/native_clients/BillingRecoveryTest.kt"
java -cp "$temp/recovery.jar:$stdlib" art.lazying.westicker.BillingRecoveryTestKt

cp="$stdlib:$coroutines:$annotations:$sdk/platforms/android-36/android.jar"
aar() {
    local file
    file="$(artifact "$1" "$2" "$3" aar)"
    unzip -q "$file" classes.jar -d "$temp/$2"
    cp+=":$temp/$2/classes.jar"
}
aar com.android.billingclient billing 8.3.0
aar androidx.compose.runtime runtime-android 1.9.0
aar androidx.compose.runtime runtime-saveable-android 1.9.0
aar androidx.compose.ui ui-android 1.9.0
aar androidx.compose.ui ui-unit-android 1.9.0
aar androidx.compose.ui ui-graphics-android 1.9.0
aar androidx.compose.ui ui-geometry-android 1.9.0
aar androidx.compose.ui ui-text-android 1.9.0
aar androidx.compose.ui ui-util-android 1.9.0
aar androidx.compose.foundation foundation-android 1.9.0
aar androidx.compose.foundation foundation-layout-android 1.9.0
aar androidx.compose.animation animation-android 1.9.0
aar androidx.compose.animation animation-core-android 1.9.0
aar androidx.compose.material3 material3-android 1.3.2
aar androidx.compose.material material-icons-core-android 1.7.8
aar androidx.compose.material material-icons-extended-android 1.7.8
plugin="$(artifact org.jetbrains.kotlin kotlin-compose-compiler-plugin-embeddable 2.2.20 jar)"
"${compile[@]}" -classpath "$cp" -Xplugin="$plugin" -d "$temp/client.jar" \
    "$sources/BillingRecovery.kt" "$sources/NativeBilling.kt" "$sources/BillingAccountScreen.kt" "$sources/StudioChrome.kt" \
    "$root/tests/native_clients/CloudStudioStub.kt"
printf 'Billing client and Compose Account typecheck passed against cached SDKs (compile-only CloudStudio boundary).\n'

if [[ ${1:-} == "--ui" ]]; then
    aar androidx.activity activity 1.11.0
    aar androidx.activity activity-ktx 1.11.0
    aar androidx.activity activity-compose 1.11.0
    aar androidx.browser browser 1.9.0
    aar androidx.core core 1.17.0
    aar androidx.core core-ktx 1.17.0
    aar androidx.lifecycle lifecycle-runtime-android 2.9.4
    aar androidx.lifecycle lifecycle-runtime-compose-android 2.9.4
    aar androidx.lifecycle lifecycle-viewmodel-android 2.9.4
    aar androidx.lifecycle lifecycle-viewmodel-savedstate-android 2.9.4
    aar androidx.savedstate savedstate-android 1.3.1
    for library in coil coil-base coil-compose coil-compose-base coil-gif; do
        aar io.coil-kt "$library" 2.7.0
    done
    cp+=":$(artifact androidx.lifecycle lifecycle-common-jvm 2.9.4 jar)"
    "${compile[@]}" -classpath "$cp" -Xplugin="$plugin" -d "$temp/native-ui.jar" "$sources"/*.kt
    printf 'All native Compose sources typechecked against cached SDKs (no app package).\n'
fi
