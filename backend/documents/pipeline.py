from .templates_engine.applier import apply_template

def template_step(doc, job):
    config_dict = job.config
    apply_template(doc, config_dict)
    return doc

PIPELINE = [
    template_step
]