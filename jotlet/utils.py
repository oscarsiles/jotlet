def generate_link_header(response, files_css=None, files_scripts=None, files_font=None, domain_preconnect=None):
    link_header = response.get("Link", "")

    if files_css:
        for file in files_css:
            link_header += f"<{file}>; rel=preload; as=style, "
    if files_font:
        for file in files_font:
            link_header += f"<{file}>; rel=preload; as=font; crossorigin=anonymous, "
    if files_scripts:
        for file in files_scripts:
            link_header += f"<{file}>; rel=preload; as=script, "
    if domain_preconnect:
        for domain in domain_preconnect:
            link_header += f"<{domain}>; rel=preconnect, "

    if link_header != "":
        response["Link"] = link_header

    return response
